#!/usr/bin/env python3
"""Portable Expedition patch; read-only unless --apply is supplied."""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import uuid
import zipfile

BUNDLE = Path(__file__).resolve().parent
PATCH_ID = 'expedition-session-20261028'
CATALOG = 'kubejs/config/expedition-selected-native-recipes.json'
BACKUPS = '.expedition-patch-backups'

class Conflict(RuntimeError):
    pass

def sha(data):
    return None if data is None else hashlib.sha256(data).hexdigest()

def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def safe_path(root, relative):
    value = str(relative)
    parts = PurePosixPath(value).parts
    if not parts or value.startswith('/') or '\\' in value or any(x in ('..', '.') for x in parts):
        raise Conflict('Unsafe relative path: ' + value)
    p = root
    for part in parts:
        p = p / part
        if p.is_symlink():
            raise Conflict('Symlink in target path: ' + str(p))
    if p.exists() and not p.is_file():
        raise Conflict('Expected a regular file: ' + str(p))
    return p

def current(path):
    return path.read_bytes() if path.exists() else None

def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('xb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()

def load_bundle():
    manifest = read_json(BUNDLE / 'manifest.json')
    if manifest.get('patchId') != PATCH_ID or manifest.get('schemaVersion') != 1:
        raise Conflict('Unrecognized package manifest')
    expected = {'install.py', 'test_installer.py', 'catalog-delta.json', 'menu/patch_menu.py'}
    expected.update('payload/' + row['path'] for row in manifest.get('payload', []))
    if not expected.issubset(manifest.get('packageFiles', {})):
        raise Conflict('Incomplete package integrity manifest')
    for name, expected in manifest['packageFiles'].items():
        p = safe_path(BUNDLE, name)
        if not p.exists() or sha(p.read_bytes()) != expected:
            raise Conflict('Package integrity check failed: ' + name)
    return manifest

def check_dependencies(instance, role, manifest):
    mods = instance / 'mods'
    if mods.is_symlink() or not mods.is_dir():
        raise Conflict('Expected an actual instance with a regular mods directory')
    found = {}
    jars = list(mods.glob('*.jar'))
    for p in jars:
        if p.is_symlink():
            raise Conflict('Symlinked mod JAR: ' + p.name)
        try:
            with zipfile.ZipFile(p) as jar:
                if 'META-INF/mods.toml' in jar.namelist():
                    text = jar.read('META-INF/mods.toml').decode('utf-8', errors='replace')
                    # Only actual [[mods]] tables identify installed mods.
                    # [[dependencies.*]] modId values may be optional/absent.
                    in_mod = False
                    for line in text.splitlines():
                        stripped = line.strip()
                        if stripped.startswith('['):
                            in_mod = bool(re.fullmatch(r'\[\[mods\]\]\s*(?:#.*)?', stripped))
                        elif in_mod:
                            match = re.match(r'\s*modId\s*=\s*[\"\x27]([^\"\x27]+)[\"\x27]', line)
                            if match:
                                found.setdefault(match.group(1), []).append(p.name)
        except (OSError, zipfile.BadZipFile) as error:
            raise Conflict('Unreadable mod JAR: ' + p.name) from error
    collisions = {'aeronautics', 'exnihilosequentia'}.intersection(found)
    if collisions:
        raise Conflict('Native recipe conditions disabled by installed mod: ' + ', '.join(sorted(collisions)))
    hashes = {}
    for row in manifest['requiredMods']:
        if role not in row['roles']:
            continue
        named = mods / row['filename']
        candidates = [named] if named.exists() else jars
        for p in candidates:
            hashes.setdefault(p, sha(p.read_bytes()))
        if not any(hashes[p] == row['sha256'] for p in candidates):
            raise Conflict('Missing/incompatible tested dependency: ' + row['filename'])
    for name in manifest['requiredBaseFiles']:
        if not safe_path(instance, name).exists():
            raise Conflict('Existing Expedition/CMI base file required: ' + name)

def merge_catalog(before, delta):
    catalog = json.loads(before.decode('utf-8-sig'))
    if catalog.get('schemaVersion') != 1 or catalog.get('mode') != 'parallel_native_and_cmi':
        raise Conflict('Catalog schema/mode differs; this is not a general modpack patch')
    count = catalog.get('selectionCount')
    if type(count) is not int or count < 0 or not isinstance(catalog.get('recipes'), list):
        raise Conflict('Invalid catalog metadata')
    by_id = {}
    for row in catalog['recipes']:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str) or row['id'] in by_id:
            raise Conflict('Invalid/duplicate catalog recipe ID')
        by_id[row['id']] = row
    added, groups = [], []
    for group in delta['groups']:
        present = [row['id'] in by_id for row in group['recipes']]
        if group['selectionIncrement'] and any(present) and not all(present):
            raise Conflict('Partial catalog group: resolve its selectionCount first: ' + group['name'])
        for row in group['recipes']:
            old = by_id.get(row['id'])
            if old is not None:
                if old.get('nativeId') != row['nativeId'] or old.get('json') != row['json']:
                    raise Conflict('Catalog recipe collision: ' + row['id'])
                continue
            catalog['recipes'].append(row)
            by_id[row['id']] = row
            added.append(row['id'])
        if not any(present) and group['selectionIncrement']:
            count += group['selectionIncrement']
            groups.append(group['name'])
    if added:
        catalog['selectionCount'] = count
    return (encoded(catalog) if added else before), {'addedRecipes': added, 'addedSelectionGroups': groups, 'selectionCount': count}

def menu_module():
    spec = importlib.util.spec_from_file_location('expedition_patch_menu', BUNDLE / 'menu/patch_menu.py')
    module = importlib.util.module_from_spec(spec)
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = old
    return module

def make_plan(instance, role, manifest):
    check_dependencies(instance, role, manifest)
    jobs = []
    report = {'patchId': PATCH_ID, 'instance': str(instance), 'role': role, 'files': []}
    def add(name, before, after, operation):
        safe_path(instance, name)
        jobs.append({'path': name, 'before': before, 'after': after})
        report['files'].append({'path': name, 'operation': operation, 'changed': before != after,
                                'beforeSha256': sha(before), 'afterSha256': sha(after)})
    p = safe_path(instance, CATALOG)
    if not p.exists():
        raise Conflict('Existing selected-native catalog required; incremental patch only')
    before = p.read_bytes()
    after, report['catalog'] = merge_catalog(before, read_json(BUNDLE / 'catalog-delta.json'))
    add(CATALOG, before, after, 'merge_recipes_preserve_other_rows')
    for row in manifest['payload']:
        if role not in row['roles']:
            continue
        name = row['path']
        before = current(safe_path(instance, name))
        after = (BUNDLE / 'payload' / name).read_bytes()
        if sha(before) not in row['acceptedBeforeSha256'] + [row['sha256']]:
            raise Conflict('Unrecognized local edit; refusing overwrite: ' + name)
        add(name, before, after, 'install_guarded_file')
    if role == 'client':
        helper = menu_module()
        retained = helper.check_retained_entry(safe_path(instance, helper.LAYOUT_RELATIVE_PATH.as_posix()).read_bytes())
        name = helper.CONFIG_RELATIVE_PATH.as_posix()
        before = safe_path(instance, name).read_bytes()
        add(name, before, helper.patch_quark_config_bytes(before), 'disable_duplicate_native_quark_q')
        report['menu'] = {'retainedEntry': retained, 'sideEffect': 'Official Quark switch also disables native pause-menu q.'}
    return jobs, report

def apply_plan(instance, role, jobs, report):
    jobs = [job for job in jobs if job['before'] != job['after']]
    if not jobs:
        report['status'] = 'already_installed'
        return report
    stamp = dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:8]
    relative_dir = BACKUPS + '/' + stamp
    safe_path(instance, relative_dir + '/receipt.json')
    backup_dir = instance / relative_dir
    backup_dir.mkdir(parents=True, exist_ok=False)
    entries = []
    for job in jobs:
        target = safe_path(instance, job['path'])
        if current(target) != job['before']:
            raise Conflict('Target changed during planning: ' + job['path'])
        backup_name = 'files/' + job['path'] if job['before'] is not None else None
        if backup_name:
            atomic_write(safe_path(backup_dir, backup_name), job['before'])
        entries.append({'path': job['path'], 'beforeSha256': sha(job['before']),
                        'afterSha256': sha(job['after']), 'backup': backup_name})
    receipt_path = backup_dir / 'receipt.json'
    receipt = {'schemaVersion': 1, 'patchId': PATCH_ID, 'instance': str(instance), 'role': role,
               'status': 'prepared', 'entries': entries, 'createdAtUtc': stamp}
    atomic_write(receipt_path, encoded(receipt))
    written = []
    try:
        for job in jobs:
            target = safe_path(instance, job['path'])
            if current(target) != job['before']:
                raise Conflict('Concurrent edit detected: ' + job['path'])
            atomic_write(target, job['after'])
            written.append(job)
            if current(target) != job['after']:
                raise Conflict('Post-write verification failed: ' + job['path'])
        receipt['status'] = 'installed'
        atomic_write(receipt_path, encoded(receipt))
    except Exception:
        for job in reversed(written):
            target = safe_path(instance, job['path'])
            if job['before'] is None:
                target.unlink()
            else:
                atomic_write(target, job['before'])
        receipt['status'] = 'failed_restored'
        atomic_write(receipt_path, encoded(receipt))
        raise
    report.update(status='installed', receipt=str(receipt_path))
    return report

def rollback(instance, receipt_path, apply):
    receipt_path = receipt_path.expanduser().absolute()
    try:
        relative = receipt_path.relative_to(instance)
    except ValueError as error:
        raise Conflict('Receipt must belong to the explicit instance') from error
    if not relative.parts or relative.parts[0] != BACKUPS:
        raise Conflict('Receipt must be inside the instance patch backup directory')
    safe_path(instance, relative.as_posix())
    receipt = read_json(receipt_path)
    if receipt.get('schemaVersion') != 1 or receipt.get('patchId') != PATCH_ID or receipt.get('instance') != str(instance):
        raise Conflict('Receipt does not match this patch/instance')
    if receipt.get('status') not in ('installed', 'rolled_back'):
        raise Conflict('Receipt is not a completed installation')
    jobs = []
    for entry in receipt['entries']:
        path = safe_path(instance, entry['path'])
        actual = current(path)
        if sha(actual) not in (entry['beforeSha256'], entry['afterSha256']):
            raise Conflict('File changed after install; rollback refused: ' + entry['path'])
        before = None
        if entry['backup']:
            before = safe_path(receipt_path.parent, entry['backup']).read_bytes()
        if sha(before) != entry['beforeSha256']:
            raise Conflict('Backup integrity failure: ' + entry['path'])
        jobs.append((path, actual, before))
    result = {'patchId': PATCH_ID, 'mode': 'rollback' if apply else 'rollback-dry-run',
              'receipt': str(receipt_path), 'files': [str(x[0].relative_to(instance)) for x in jobs]}
    if apply:
        written = []
        try:
            for path, actual, before in jobs:
                if current(path) != actual:
                    raise Conflict('Concurrent edit detected during rollback')
                if before is None:
                    if path.exists():
                        path.unlink()
                else:
                    atomic_write(path, before)
                written.append((path, actual, before))
            receipt['status'] = 'rolled_back'
            atomic_write(receipt_path, encoded(receipt))
        except Exception:
            for path, actual, before in reversed(written):
                if actual is None:
                    if path.exists():
                        path.unlink()
                else:
                    atomic_write(path, actual)
            raise
        result['status'] = 'rolled_back'
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', required=True, type=Path, help='Actual launcher client/server root')
    parser.add_argument('--role', choices=('client', 'server'), help='Required except for rollback')
    parser.add_argument('--apply', action='store_true', help='Write changes; otherwise read-only')
    parser.add_argument('--verify', action='store_true', help='Read-only: fail if changes are still needed')
    parser.add_argument('--rollback', type=Path, metavar='RECEIPT', help='Plan rollback; add --apply to perform it')
    args = parser.parse_args(argv)
    if args.verify and (args.apply or args.rollback):
        parser.error('--verify cannot be combined with --apply or --rollback')
    if not args.rollback and not args.role:
        parser.error('--role is required for install/verify')
    instance = args.instance.expanduser().absolute()
    if instance.is_symlink() or not instance.is_dir() or instance.resolve() != instance:
        raise Conflict('Use the real instance directory without symlink ancestors')
    if tuple(instance.parts[-3:]) == ('clients', 'cmi-expedition', 'instance'):
        raise Conflict('Retired desktop client copy refused; choose the real launcher profile')
    if args.rollback:
        result = rollback(instance, args.rollback, args.apply)
    else:
        manifest = load_bundle()
        jobs, result = make_plan(instance, args.role, manifest)
        result['mode'] = 'verify' if args.verify else 'apply' if args.apply else 'dry-run'
        changed = any(job['before'] != job['after'] for job in jobs)
        if args.verify:
            result['status'] = 'needs_installation' if changed else 'verified_installed'
        elif args.apply:
            result = apply_plan(instance, args.role, jobs, result)
        else:
            result['status'] = 'changes_planned' if changed else 'already_installed'
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('status') == 'needs_installation' else 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (Conflict, ValueError, OSError, KeyError) as error:
        print('Patch refused: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
