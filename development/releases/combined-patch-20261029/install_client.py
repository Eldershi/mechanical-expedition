#!/usr/bin/env python3
"""Install the combined Expedition client patch transactionally (Python 3.9+).

Default is a read-only check. Use --apply to install, or --rollback BACKUP to
restore the exact files saved by a previous transaction. No force mode exists.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import tempfile
import uuid
import sys
import bundle_support

SCHEMA = 1
PROTECTED_CATALOGS = (
    'kubejs/config/expedition-selected-native-recipes.json',
    'kubejs/config/expedition-pre-steam-recipes.json',
    'kubejs/config/expedition-material-unification.json',
)
ROOTS = frozenset(('mods', 'kubejs', 'config', 'defaultconfigs', 'ldlib',
                   'hotai', 'resourcepacks', 'tlm_custom_pack'))
EXCLUDED_PREFIXES = ('kubejs/exported/', 'kubejs/probe/', 'kubejs/logs/',
                     'config/jei/', 'config/jade/', 'config/fancymenu/')
EXCLUDED_NAMES = frozenset(('.DS_Store', 'server.properties', 'eula.txt',
                           'options.txt', 'optionsof.txt', 'servers.dat',
                           'usernamecache.json', 'usercache.json'))
SHA = re.compile(r'[0-9a-f]{64}\Z')


class PatchError(RuntimeError):
    pass


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def relative_path(value):
    if not isinstance(value, str) or not value or '\\' in value or '\0' in value:
        raise PatchError('Invalid manifest path: ' + repr(value))
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in ('', '.', '..') for part in path.parts) or path.as_posix() != value:
        raise PatchError('Unsafe manifest path: ' + value)
    return path


def eligible(value):
    path = relative_path(value)
    if path.parts[0] not in ROOTS or any(part in EXCLUDED_NAMES for part in path.parts):
        return False
    if value.startswith(EXCLUDED_PREFIXES):
        return False
    if value.startswith('kubejs/config/') and ('probe' in path.name or path.name in ('client.properties', 'defaultoptions.txt')):
        return False
    return not any(part in ('.git', '__pycache__') for part in path.parts)


def safe_path(root, rel):
    parts = relative_path(rel).parts
    if root.is_symlink():
        raise PatchError('Target root may not be a symbolic link: ' + str(root))
    path = root
    for part in parts:
        path = path / part
        if path.is_symlink():
            raise PatchError('Symbolic link rejected: ' + str(path))
    if path.exists() and not path.is_file():
        raise PatchError('Expected regular file: ' + str(path))
    return path


def current_hash(root, rel):
    path = safe_path(root, rel)
    return digest(path) if path.is_file() else None


def read_json(path):
    if path.is_symlink() or not path.is_file():
        raise PatchError('Expected regular JSON file: ' + str(path))
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    handle, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(handle, 'wb') as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def atomic_copy(source, target, mode=0o644):
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix='.expedition-patch-', dir=target.parent)
    try:
        with source.open('rb') as src, os.fdopen(handle, 'wb') as out:
            shutil.copyfileobj(src, out, 1024 * 1024)
            out.flush()
            os.fsync(out.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def exclusive_lock(root):
    lock = root / '.expedition-client-patch.lock'
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as error:
        raise PatchError('Another patch transaction holds ' + str(lock)) from error
    try:
        with os.fdopen(fd, 'w') as out:
            out.write(json.dumps({'pid': os.getpid(), 'createdAt': datetime.now(timezone.utc).isoformat()}))
        yield
    finally:
        lock.unlink(missing_ok=True)


def validate_manifest(manifest):
    if manifest.get('schemaVersion') != SCHEMA:
        raise PatchError('Unsupported client manifest schema')
    patch_id = manifest.get('patchId', '')
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,100}', patch_id):
        raise PatchError('Invalid patch ID')
    catalogs = manifest.get('protectedCatalogs', {})
    if set(catalogs) != set(PROTECTED_CATALOGS) or not all(SHA.fullmatch(x or '') for x in catalogs.values()):
        raise PatchError('Three protected catalog hashes are required')
    seen = set()
    if not isinstance(manifest.get('operations'), list):
        raise PatchError('Manifest operations must be a list')
    for op in manifest['operations']:
        rel = op.get('path')
        if rel in seen or not eligible(rel) or rel in PROTECTED_CATALOGS:
            raise PatchError('Unauthorized or duplicate operation: ' + str(rel))
        seen.add(rel)
        before, after = op.get('beforeSha256'), op.get('afterSha256')
        if not all(x is None or SHA.fullmatch(x) for x in op.get('acceptedBeforeSha256', [])):
            raise PatchError('Invalid accepted-before SHA: ' + rel)
        if before is not None and not SHA.fullmatch(before):
            raise PatchError('Invalid before SHA: ' + rel)
        if op.get('action') == 'write':
            if not SHA.fullmatch(after or '') or before == after:
                raise PatchError('Invalid write hashes: ' + rel)
        elif op.get('action') == 'delete':
            if before is None or after is not None:
                raise PatchError('Invalid deletion hashes: ' + rel)
        else:
            raise PatchError('Unsupported action: ' + str(op.get('action')))


def preflight(root, package, manifest):
    root = Path(root).absolute()
    package = Path(package).absolute()
    if not root.is_dir() or root.is_symlink():
        raise PatchError('Instance must be an existing real directory')
    if tuple(root.parts[-3:]) == ('clients', 'cmi-expedition', 'instance'):
        raise PatchError('Retired desktop copy rejected; select the actual launcher instance')
    integrity = read_json(package / 'package-integrity.json')
    for rel, wanted in integrity['files'].items():
        source = safe_path(package, rel)
        if not source.is_file() or digest(source) != wanted:
            raise PatchError('Package integrity check failed: ' + rel)
    validate_manifest(manifest)
    extras = bundle_support.prepare(root, package, manifest, sys.modules[__name__])
    projected = {op['path']: op['afterSha256'] for op in extras}
    conflicts, operations = [], []
    for rel, wanted in manifest['protectedCatalogs'].items():
        observed = projected.get(rel, current_hash(root, rel))
        if observed != wanted:
            conflicts.append({'path': rel, 'reason': 'protected_catalog_changed', 'expected': wanted, 'observed': observed})
    payload = package / 'client-payload'
    for op in manifest['operations']:
        observed = current_hash(root, op['path'])
        after = op['afterSha256']
        if observed == after:
            state = 'already_applied'
        elif observed in [op['beforeSha256']] + op.get('acceptedBeforeSha256', []):
            state = 'pending'
        else:
            state = 'conflict'
            conflicts.append({'path': op['path'], 'reason': 'target_changed_since_snapshot',
                              'expectedBefore': op['beforeSha256'], 'expectedAfter': after, 'observed': observed})
        if op['action'] == 'write':
            source = safe_path(payload, op['path'])
            if not source.is_file() or digest(source) != after:
                conflicts.append({'path': op['path'], 'reason': 'payload_missing_or_hash_mismatch'})
        operations.append({**op, 'observedSha256': observed, 'state': state})
    seen = {op['path'] for op in operations}
    for op in extras:
        if op['path'] in seen or not bundle_support.authorized_extra(op['path'], package):
            raise PatchError('Unauthorized or overlapping generated operation: ' + op['path'])
        seen.add(op['path'])
        operations.append(op)
    if conflicts:
        raise PatchError('Preflight refused without writing target files:\n' + json.dumps(conflicts, ensure_ascii=False, indent=2))
    bundle_support.check_duplicates(root, package, operations, sys.modules[__name__])
    return {'passed': True, 'pending': sum(x['state'] == 'pending' for x in operations),
            'alreadyApplied': sum(x['state'] == 'already_applied' for x in operations), 'operations': operations}


def _restore(root, backup, transaction, package):
    entries = transaction['entries']
    conflicts = []
    for entry in entries:
        rel = entry['path']
        if ((not eligible(rel) or rel in PROTECTED_CATALOGS)
                and not bundle_support.authorized_extra(rel, package)):
            raise PatchError('Unauthorized rollback path: ' + rel)
        observed = current_hash(root, rel)
        if observed not in (entry['originalSha256'], entry['installedSha256']):
            conflicts.append({'path': rel, 'reason': 'target_changed_after_install', 'observed': observed})
        if entry['originalSha256'] is not None:
            source = safe_path(backup / 'files', rel)
            if not source.is_file() or digest(source) != entry['originalSha256']:
                conflicts.append({'path': rel, 'reason': 'backup_missing_or_hash_mismatch'})
    if conflicts:
        raise PatchError('Rollback refused to overwrite later changes:\n' + json.dumps(conflicts, ensure_ascii=False, indent=2))
    restored = 0
    for entry in reversed(entries):
        rel = entry['path']
        if current_hash(root, rel) == entry['originalSha256']:
            continue
        target = safe_path(root, rel)
        if entry['originalSha256'] is None:
            target.unlink()
        else:
            atomic_copy(backup / 'files' / rel, target, entry['mode'])
            os.utime(target, ns=(entry['atimeNs'], entry['mtimeNs']))
        if current_hash(root, rel) != entry['originalSha256']:
            raise PatchError('Rollback verification failed: ' + rel)
        restored += 1
    transaction['status'] = 'rolled_back'
    transaction['rolledBackAt'] = datetime.now(timezone.utc).isoformat()
    transaction['restoredFiles'] = restored
    write_json(backup / 'transaction.json', transaction)
    return {'status': 'rolled_back', 'restoredFiles': restored, 'backup': str(backup)}


def rollback(root, backup, package):
    root, backup = Path(root).absolute(), Path(backup).absolute()
    transaction = read_json(backup / 'transaction.json')
    if transaction.get('schemaVersion') != SCHEMA or Path(transaction['root']).absolute() != root:
        raise PatchError('Backup transaction belongs to another instance')
    if not str(backup).startswith(str(root / '.expedition-patch-backups') + os.sep):
        raise PatchError('Backup must belong to this instance backup directory')
    for ancestor in [backup, *backup.parents]:
        if ancestor == root:
            break
        if ancestor.is_symlink():
            raise PatchError('Symbolic link rejected in backup directory: ' + str(ancestor))
    with exclusive_lock(root):
        return _restore(root, backup, transaction, package)


def install(root, package, manifest):
    root, package = Path(root).absolute(), Path(package).absolute()
    if manifest.get('validationStatus') != 'validated':
        raise PatchError('Preview/unvalidated packages cannot be installed')
    if not root.is_dir() or root.is_symlink():
        raise PatchError('Instance must be an existing real directory')
    with exclusive_lock(root):
        checked = preflight(root, package, manifest)
        pending = [x for x in checked['operations'] if x['state'] == 'pending']
        if not pending:
            return {'status': 'already_applied', 'changedFiles': 0, 'backup': None}
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:12]
        backup = root / '.expedition-patch-backups' / manifest['patchId'] / stamp
        for ancestor in [backup.parent, *backup.parent.parents]:
            if ancestor == root:
                break
            if ancestor.is_symlink():
                raise PatchError('Symbolic link rejected in backup directory: ' + str(ancestor))
        backup.mkdir(parents=True)
        transaction = {'schemaVersion': SCHEMA, 'patchId': manifest['patchId'], 'root': str(root),
                       'status': 'preparing', 'createdAt': datetime.now(timezone.utc).isoformat(),
                       'manifestSha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(), 'entries': []}
        for op in pending:
            rel = op['path']
            target = safe_path(root, rel)
            info = target.stat() if target.is_file() else None
            entry = {'path': rel, 'originalSha256': op['observedSha256'], 'installedSha256': op['afterSha256'],
                     'action': op['action'], 'mode': stat.S_IMODE(info.st_mode) if info else 0o644,
                     'atimeNs': info.st_atime_ns if info else None, 'mtimeNs': info.st_mtime_ns if info else None}
            if info:
                saved = backup / 'files' / rel
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                with saved.open('rb') as stored:
                    os.fsync(stored.fileno())
                if digest(saved) != entry['originalSha256'] or current_hash(root, rel) != entry['originalSha256']:
                    raise PatchError('Target changed while backing up; installation not started: ' + rel)
            transaction['entries'].append(entry)
            if op.get('generatedHex') is not None:
                prepared = safe_path(backup / 'prepared', rel)
                prepared.parent.mkdir(parents=True, exist_ok=True)
                prepared.write_bytes(bytes.fromhex(op['generatedHex']))
                if digest(prepared) != op['afterSha256']:
                    raise PatchError('Generated file changed: ' + rel)
        transaction['status'] = 'prepared'
        write_json(backup / 'transaction.json', transaction)
        try:
            for entry in transaction['entries']:
                rel = entry['path']
                if current_hash(root, rel) != entry['originalSha256']:
                    raise PatchError('Target changed after backup: ' + rel)
                target = safe_path(root, rel)
                if entry['action'] == 'delete':
                    target.unlink()
                else:
                    prepared = safe_path(backup / 'prepared', rel)
                    source = prepared if prepared.is_file() else safe_path(package / 'client-payload', rel)
                    atomic_copy(source, target, entry['mode'])
                if current_hash(root, rel) != entry['installedSha256']:
                    raise PatchError('Installed file hash verification failed: ' + rel)
            for op in manifest['operations']:
                if current_hash(root, op['path']) != op['afterSha256']:
                    raise PatchError('Final verification failed: ' + op['path'])
            for rel, wanted in manifest['protectedCatalogs'].items():
                if current_hash(root, rel) != wanted:
                    raise PatchError('Protected catalog changed during installation: ' + rel)
            if bundle_support.prepare(root, package, manifest, sys.modules[__name__]):
                raise PatchError('Prerequisite or HNN resource order did not converge')
        except Exception as error:
            transaction['error'] = str(error)
            try:
                _restore(root, backup, transaction, package)
            except Exception as restore_error:
                transaction['status'] = 'rollback_conflict'
                transaction['rollbackError'] = str(restore_error)
                write_json(backup / 'transaction.json', transaction)
                raise PatchError('Installation failed; automatic rollback needs attention. Backup: ' + str(backup) + '\n' + str(restore_error)) from error
            raise PatchError('Installation failed and was rolled back. Backup: ' + str(backup) + '\n' + str(error)) from error
        transaction['status'] = 'complete'
        transaction['completedAt'] = datetime.now(timezone.utc).isoformat()
        write_json(backup / 'transaction.json', transaction)
        return {'status': 'installed', 'changedFiles': len(pending), 'alreadyApplied': checked['alreadyApplied'], 'backup': str(backup)}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--root', type=Path, required=True, help='Active launcher instance directory')
    cli.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    action = cli.add_mutually_exclusive_group()
    action.add_argument('--apply', action='store_true')
    action.add_argument('--verify', action='store_true', help='Read-only; exit 1 if any update remains')
    action.add_argument('--rollback', type=Path, metavar='BACKUP_DIRECTORY')
    args = cli.parse_args()
    if args.rollback:
        result = rollback(args.root, args.rollback, args.package)
    else:
        manifest = read_json(args.package / 'client-manifest.json')
        result = install(args.root, args.package, manifest) if args.apply else preflight(args.root, args.package, manifest)
        if not args.apply:
            result.pop('operations', None)
            result['status'] = 'verified' if args.verify and result['pending'] == 0 else 'checked_without_changes'
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.verify and result.get('pending', 0):
        raise SystemExit(1)


if __name__ == '__main__':
    try:
        main()
    except (PatchError, OSError, ValueError) as error:
        raise SystemExit(str(error))
