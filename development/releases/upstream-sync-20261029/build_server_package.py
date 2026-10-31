#!/usr/bin/env python3
"""Build a reviewed server runtime or an exact, reversible live-server delta.

No deployment is performed. --check only writes plans. Final archives require
passing --validation-report JSON files and include hashes for every operation.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from decimal import Decimal
import re
from pathlib import Path
import shutil
import sys
import tempfile
import zipfile
import install_client as common
from server_package_rules import PRESERVE_REMOTE, overlay_decision, runtime_server_overlays, live_server_additions

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
SERVER = PROJECT / 'servers/cmi-expedition'
sys.path.insert(0, str(SERVER))
import prepare_server as server_tools
from deployment_mod_overlays import load_mod_overlays, load_server_additions

ROOTS = ('mods', 'config', 'defaultconfigs', 'kubejs', 'ldlib', 'hotai',
         'patchouli_books', 'moonlight-global-datapacks', 'datapacks', 'tlm_custom_pack')
SNAPSHOT_ROOTS = ('mods', 'config', 'kubejs', 'ldlib', 'hotai')
REQUIRED_DIRS = ('kubejs/exported',)
TRANSIENT_PREFIXES = ('config/spark/tmp/',)
SKIP_PARTS = {'.DS_Store', '.git', '__pycache__', '.cache', 'exported', 'probe',
              'logs', 'crash-reports', 'client_scripts', 'saves'}
SKIP_CONFIG = tuple('config/' + p for p in sorted(server_tools.SKIP_CONFIG)) + (
    'config/jei/', 'config/jade/', 'config/xaerominimap/', 'config/xaeroworldmap/')
SKIP_NAMES = {'server.properties', 'eula.txt', 'options.txt', 'servers.dat',
              'usernamecache.json', 'usercache.json', 'client.properties',
              'probe-settings.json', 'probejs.json', 'defaultoptions.txt'}


def quest_semantics(path):
    spec = importlib.util.spec_from_file_location('merge_content_parser', HERE / 'tools/merge_content.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    def normalized(value, key='', depth=0):
        if isinstance(value, module.Number):
            return Decimal(re.sub('[bBsSlLfFdD]$', '', value)).normalize()
        if isinstance(value, list):
            return [normalized(v, '', depth + 1) for v in value]
        if isinstance(value, dict):
            if key in ('icon', 'item') and 'id' in value:
                # FTB expands a plain icon into its default empty ItemStack.
                rest = {k: v for k, v in value.items() if k not in ('id', 'Count', 'ForgeCaps')}
                tag = rest.get('tag', {})
                caps = value.get('ForgeCaps', {})
                empty_caps = all(isinstance(v, dict) and not v.get('Items') for v in caps.values())
                default_damage = set(tag).issubset({'Damage', 'graphDmg'}) and all(str(v) in ('0', '0b') for v in tag.values())
                if (not rest or set(rest) == {'tag'}) and default_damage and empty_caps and str(value.get('Count', '1')) in ('1', '1b'):
                    return value['id']
            result = {}
            for k, v in value.items():
                if depth == 0 and k == 'order_index':
                    continue
                if v is False and (k in ('optional', 'dev') or k.startswith('quest_enhance_')):
                    continue
                if v == [] and k in ('rewards', 'hover', 'quest_enhance_hidden_dependency_lines',
                                      'quest_enhance_decorative_lines', 'quest_links'):
                    continue
                if k == 'alpha' and isinstance(v, module.Number) and Decimal(v) == 255:
                    continue
                if k in ('size', 'count') and isinstance(v, module.Number) and Decimal(re.sub('[bBsSlLfFdD]$', '', v)) == 1:
                    continue
                result[k] = normalized(v, k, depth + 1)
            return result
        return value
    return normalized(module.loads(Path(path).read_text()))


def same_runtime(left, right, rel):
    if not right.is_file() or right.is_symlink():
        return False
    if common.digest(left) == common.digest(right):
        return True
    return rel.startswith('config/ftbquests/') and rel.endswith('.snbt') and quest_semantics(left) == quest_semantics(right)


def critical_path(rel):
    if excluded(rel) == 'preserve live server control/state':
        return False
    if rel.startswith('mods/'):
        return rel.endswith('.jar')
    if rel.startswith(('kubejs/server_scripts/', 'kubejs/startup_scripts/')):
        return rel.endswith('.js')
    if rel.startswith('config/ftbquests/quests/'):
        return rel.endswith('.snbt')
    if rel.startswith('kubejs/data/'):
        return rel.endswith(('.json', '.nbt', '.mcmeta'))
    if rel.startswith('kubejs/config/'):
        return rel.endswith(('.json', '.properties')) and rel != 'kubejs/config/release-sync-runtime.json'
    return False


def files(root):
    root = Path(root)
    if root.is_symlink():
        raise common.PatchError('Symbolic runtime root: ' + str(root))
    if root.exists():
        for path in sorted(root.rglob('*')):
            if path.is_symlink():
                raise common.PatchError('Symbolic runtime file: ' + str(path))
            if path.is_file():
                yield path


def transient_path(rel):
    return any(rel == p.rstrip('/') or rel.startswith(p) for p in TRANSIENT_PREFIXES)


def excluded(rel, fixtures=()):
    parts = common.relative_path(rel).parts
    if parts[0] not in ROOTS:
        return 'outside runtime roots'
    if transient_path(rel):
        return 'volatile runtime cache'
    if set(parts) & SKIP_PARTS or parts[-1] in SKIP_NAMES:
        return 'client/generated/machine-local'
    if parts[-1] in fixtures or parts[-1] == 'UpstreamMachineSelectionAudit.js':
        return 'validation fixture'
    if parts[-1].endswith(('.disabled', '.bak', '.tmp', '.log')):
        return 'inactive/generated'
    for prefix in PRESERVE_REMOTE:
        if rel == prefix.rstrip('/') or rel.startswith(prefix if prefix.endswith('/') else prefix + '/'):
            return 'preserve live server control/state'
    for prefix in SKIP_CONFIG:
        if rel == prefix.rstrip('/') or rel.startswith(prefix if prefix.endswith('/') else prefix + '/'):
            return 'client interface/resource config'
    if parts[0] in ('config', 'defaultconfigs') and (
            parts[-1].endswith(('-client.toml', '-client.snbt')) or parts[-1] == 'client-config.snbt'):
        return 'client configuration'
    return None


def tree_hash(rows):
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r['path']):
        h.update((row['path'] + '\0' + row['sha256'] + '\0' + str(row['bytes']) + '\n').encode())
    return h.hexdigest()


def content(staging, deployment, fixtures):
    selected, omissions, decisions = {}, [], []
    for root in ROOTS:
        if root == 'mods':
            continue
        for path in files(staging / root):
            rel = path.relative_to(staging).as_posix()
            reason = excluded(rel, fixtures)
            if reason:
                omissions.append({'path': rel, 'source': 'staging', 'reason': reason})
            else:
                selected[rel] = {'source': path, 'origin': 'merged staging'}
    for root in ('config', 'kubejs'):
        for path in files(deployment / root):
            rel = path.relative_to(deployment).as_posix()
            reason = excluded(rel, fixtures)
            decision = overlay_decision(rel, rel in selected)
            if reason:
                omissions.append({'path': rel, 'source': 'deployment', 'reason': reason})
                continue
            if decision.startswith('apply '):
                selected[rel] = {'source': path, 'origin': 'dedicated deployment overlay'}
            decisions.append({'path': rel, 'decision': decision,
                              'deploymentSha256': common.digest(path)})
    return selected, omissions, decisions


def verify_mutantmore(source, prepared):
    from patch_mutantmore_server import CONFIG, MIXIN, UPSTREAM_SHA256
    if common.digest(source) != UPSTREAM_SHA256:
        raise common.PatchError('Unreviewed MutantMore source')
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(prepared) as after:
        if before.namelist() != after.namelist() or after.testzip() is not None:
            raise common.PatchError('MutantMore ZIP membership differs')
        if [n for n in before.namelist() if before.read(n) != after.read(n)] != [CONFIG]:
            raise common.PatchError('MutantMore changed unrelated members')
        expected = json.loads(before.read(CONFIG))
        expected['client'].remove(MIXIN)
        expected['mixins'].append(MIXIN)
        if json.loads(after.read(CONFIG)) != expected:
            raise common.PatchError('MutantMore mixin fix differs')


def removal_policy():
    """Enforce removal/addition artifacts without the old client's exact count."""
    path = PROJECT / 'clients/cmi-expedition/mod-removal-20261018.json'
    policy = common.read_json(path)
    if policy.get('schemaVersion') != 1:
        raise common.PatchError('Unsupported removal policy')
    names, ids, additions = set(), set(), {}
    for key in ('removed', 'approvedAdditions'):
        for row in policy.get(key, []):
            name, declared = row['file'], row['modIds']
            if (Path(name).name != name or not name.endswith('.jar') or name in names or
                    not declared or len(declared) != len(set(declared)) or ids & set(declared) or
                    re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')) is None):
                raise common.PatchError('Invalid removal policy artifact: ' + name)
            names.add(name)
            ids.update(declared)
            if key == 'approvedAdditions':
                additions[name] = row
    return {**policy, 'removedFiles': {r['file'] for r in policy['removed']},
            'removedIds': {i for r in policy['removed'] for i in r['modIds']},
            'additionFiles': additions, 'sha256': common.digest(path)}


def jar_metadata(path):
    rows = server_tools.metadata(path.read_bytes())
    # Connector loads Fabric metadata, including the existing maid-spell mod.
    # The old prepare_server helper reads Forge mods.toml only.
    with zipfile.ZipFile(path) as archive:
        if 'META-INF/maidspell/maidspell-mod.jar' in archive.namelist():
            rows.extend(server_tools.metadata(archive.read('META-INF/maidspell/maidspell-mod.jar'), nested=True))
        if 'fabric.mod.json' in archive.namelist():
            fabric = json.loads(archive.read('fabric.mod.json'))
            if fabric.get('id') not in {i for row in rows for i in row['ids']}:
                rows.append({'ids': [fabric['id']], 'dependencies': {}, 'nested': False, 'fabric': True})
    return rows


def mods(staging, validation, server, release):
    policy = removal_policy()
    overlays = load_mod_overlays(server)
    overlays.update(runtime_server_overlays(release))
    additions = load_server_additions(server)
    additions.update(live_server_additions(release))
    expected, omissions = {}, []
    for jar in files(staging / 'mods'):
        if '.index' in jar.relative_to(staging / 'mods').parts or jar.name == '.DS_Store':
            continue
        if jar.suffix != '.jar' or jar.parent != staging / 'mods':
            raise common.PatchError('Unexpected staged mod file: ' + str(jar))
        rows = jar_metadata(jar)
        ids = {i for row in rows if not row['nested'] for i in row['ids']}
        all_ids = {i for row in rows for i in row['ids']}
        reason = ('persistent user removal' if server_tools.is_removed(jar.name, all_ids, policy) else
                  'client-only' if ids & server_tools.CLIENT_ONLY or jar.name.startswith('CrosshairBobbing') else None)
        if reason:
            omissions.append({'file': jar.name, 'modIds': sorted(ids), 'reason': reason})
        else:
            expected[jar.name] = (jar, ids)
    actual = {}
    for path in files(validation / 'mods'):
        if path.suffix != '.jar':
            continue  # Captured production .jar.before-* archives are inactive.
        if path.parent != validation/'mods':
            raise common.PatchError('Unexpected nested validation JAR: ' + str(path))
        actual[path.name] = path
    if set(actual) != set(expected) | set(additions) or set(expected) & set(additions):
        raise common.PatchError('Validation mod set differs: ' + repr({
            'missing': sorted((set(expected) | set(additions)) - set(actual)),
            'unexpected': sorted(set(actual) - set(expected) - set(additions))}))
    if set(overlays) - set(expected):
        raise common.PatchError('Required dedicated overlay no longer selected')
    selected, entries, providers, metadata = {}, [], {}, []
    for name, prepared in sorted(actual.items()):
        digest = common.digest(prepared)
        entry = {'file': name, 'sha256': digest, 'bytes': prepared.stat().st_size}
        if name in additions:
            if digest != additions[name]['sha256']:
                raise common.PatchError('Server addition differs: ' + name)
            entry.update({'patchId': additions[name]['patchId'], 'serverOnly': True})
        else:
            original, ids = expected[name]
            entry['upstreamSha256'] = common.digest(original)
            if name in overlays:
                overlay = overlays[name]
                if entry['upstreamSha256'] not in (overlay['upstreamSha256'], overlay['patchedSha256']) or digest != overlay['patchedSha256']:
                    raise common.PatchError('Dedicated patched mod differs: ' + name)
                entry['patchId'] = overlay['patchId']
            elif 'mutantmore' in ids:
                verify_mutantmore(original, prepared)
                entry['patchId'] = 'mutantmore-map-decoration-common-mixin'
            elif digest != entry['upstreamSha256']:
                raise common.PatchError('Unreviewed dedicated JAR change: ' + name)
        rows = jar_metadata(prepared)
        primary = {i for r in rows if not r['nested'] for i in r['ids']}
        for mod_id in primary:
            if mod_id in providers:
                raise common.PatchError('Duplicate server mod ID: ' + mod_id)
            providers[mod_id] = name
        entry['modIds'] = sorted(primary)
        entry['embeddedModIds'] = sorted({i for r in rows if r['nested'] for i in r['ids']})
        if primary & server_tools.CLIENT_ONLY:
            raise common.PatchError('Client-only mod in dedicated selection: ' + name)
        metadata.extend((name, row) for row in rows)
        selected['mods/' + name] = {'source': prepared, 'origin': 'validated dedicated mod'}
        entries.append(entry)
    # Upstream may upgrade formerly approved additions. Enforce persistent
    # removals here; every selected new artifact is already SHA-checked against
    # staging or a reviewed dedicated overlay above.
    server_tools.validate_mod_rows(entries, {**policy, 'additionFiles': {}})
    available = set(providers) | {i for r in entries for i in r['embeddedModIds']} | {
        'forge', 'minecraft', 'javafml', 'lowcodefml', 'mclanguage'}
    for name, row in metadata:
        deps = row['dependencies'] or {}
        if isinstance(deps, list):
            deps = {','.join(row['ids']): deps}
        for owner, requirements in deps.items():
            for dep in requirements:
                if dep.get('mandatory') and dep.get('side', 'BOTH') != 'CLIENT' and dep['modId'] not in available:
                    raise common.PatchError('Missing server dependency: ' + repr((name, owner, dep)))
    return selected, entries, omissions, policy['sha256']


def plan(release, staging=None, validation=None, server=SERVER):
    release, server = Path(release).absolute(), Path(server).absolute()
    staging = Path(staging).absolute() if staging else release / 'staging'
    validation = Path(validation).absolute() if validation else release / 'validation'
    fixtures = {p.name for p in files(release / 'validation-only')}
    selected, omissions, decisions = content(staging, server / 'deployment', fixtures)
    mod_files, mod_rows, excluded_mods, policy_sha = mods(staging, validation, server, release)
    selected.update(mod_files)
    baseline = common.read_json(release / 'evidence/active-before.json')['files']
    protected = {}
    for rel in common.PROTECTED_CATALOGS:
        expected = baseline.get(rel, {}).get('sha256')
        if not expected or rel not in selected or common.digest(selected[rel]['source']) != expected:
            raise common.PatchError('Protected restored catalog changed: ' + rel)
        protected[rel] = expected
    differences = []
    for rel, row in selected.items():
        if not rel.startswith(('kubejs/server_scripts/', 'kubejs/startup_scripts/',
                               'kubejs/data/', 'kubejs/config/', 'config/ftbquests/')):
            continue
        tested = validation / rel
        if not same_runtime(row['source'], tested, rel):
            differences.append({'path': rel, 'origin': row['origin']})
    rows = [{'path': rel, 'sha256': common.digest(row['source']), 'bytes': row['source'].stat().st_size,
             'origin': row['origin']} for rel, row in sorted(selected.items())]
    manifest = {
        'schemaVersion': 1, 'packageId': 'expedition-upstream-sync-20261029-server',
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'baseCommit': 'a87ff71c8aaeca32d3eab224d15994c70b1e7473',
        'upstreamCommit': '77f6e7adafa60007b34f464e8e810bd699649bdd',
        'sources': {'staging': str(staging), 'validation': str(validation), 'deployment': str(server / 'deployment')},
        'files': rows, 'runtimeSha256': tree_hash(rows), 'runtimeRoots': list(ROOTS),
        'directoryHashes': {root: {'sha256': tree_hash([r for r in rows if r['path'].startswith(root + '/')]),
                                   'files': sum(r['path'].startswith(root + '/') for r in rows)} for root in ROOTS},
        'mods': mod_rows, 'excludedMods': excluded_mods, 'protectedCatalogs': protected,
        'preserveRemotePaths': list(PRESERVE_REMOTE),
        'runtimeRequiredDirectories': list(REQUIRED_DIRS),
        'replacementRule': 'Rename original runtime roots into one backup before extraction; include preserved live state and extra files; never delete originals.',
        'untouchedRootPaths': ['world directories', 'libraries/', 'server.properties', 'eula.txt', 'user_jvm_args.txt',
                               'server.jar', 'run.sh', 'run.bat', 'ops.json', 'whitelist.json', 'banned-players.json'],
        'excludedFiles': omissions, 'overlayDecisions': decisions,
        'omittedTransientFiles': [r for r in omissions if transient_path(r['path'])],
        'differencesFromValidation': differences,
        'removalPolicySha256': policy_sha,
        'hashFormat': 'sha256(sorted(path UTF-8 + NUL + file sha256 + NUL + decimal bytes + LF))',
        'summary': {'files': len(rows), 'serverMods': len(mod_rows), 'clientOrRemovedModsExcluded': len(excluded_mods),
                    'runtimeBytes': sum(r['bytes'] for r in rows), 'worldsIncluded': False, 'librariesIncluded': False,
                    'fixtureNamesExcluded': sorted(fixtures | {'UpstreamMachineSelectionAudit.js'})},
    }
    return selected, manifest


def delta_plan(selected, manifest, live, release, server=SERVER):
    """Preserve live-only edits and reject unknown overlapping changes."""
    live, release, server = Path(live).absolute(), Path(release).absolute(), Path(server).absolute()
    snapshot_path = release / 'evidence/live-before-manifest.json'
    snapshot = common.read_json(snapshot_path)['files']
    baseline = common.read_json(release / 'evidence/active-before.json')['files']
    active_root = Path(common.read_json(release / 'evidence/active-before.json')['instance'])
    actual = {p.relative_to(live).as_posix(): p for p in files(live)}
    if set(actual) != set(snapshot):
        raise common.PatchError('Live snapshot membership changed since capture')
    for rel, path in actual.items():
        if common.digest(path) != snapshot[rel]['sha256']:
            raise common.PatchError('Live snapshot SHA changed: ' + rel)
    operations, preserved, conflicts, final = [], [], [], dict(selected)
    def ancestors(rel):
        values = {baseline[rel]['sha256']} if rel in baseline else set()
        for root in (server / 'instance', server / 'deployment'):
            path = root / rel
            if path.is_file() and not path.is_symlink():
                values.add(common.digest(path))
        return values
    desired_ids = {i for row in manifest['mods'] for i in row['modIds']}
    policy = removal_policy()
    fixtures = set(manifest['summary']['fixtureNamesExcluded'])
    for rel, item in sorted(selected.items()):
        if transient_path(rel):
            final.pop(rel, None)
            continue
        if rel.split('/')[0] not in SNAPSHOT_ROOTS:
            preserved.append({'path': rel, 'reason': 'remote root was not captured; no delta operation'})
            final.pop(rel, None)
            continue
        target_sha = common.digest(item['source'])
        old_sha = snapshot.get(rel, {}).get('sha256')
        if old_sha == target_sha:
            continue
        if old_sha is not None and same_runtime(item['source'], actual[rel], rel):
            final[rel] = {'source': actual[rel], 'origin': 'preserved semantically identical production serialization'}
            preserved.append({'path': rel, 'reason': 'identical quest semantics; retain production IDs/serialization', 'sha256': old_sha})
            continue
        bases = ancestors(rel)
        saved_quest_normalization = False
        if old_sha is not None and rel.startswith('config/ftbquests/') and rel.endswith('.snbt'):
            candidates = [server/'instance'/rel, server/'deployment'/rel]
            active_base = active_root/rel
            if (rel in baseline and active_base.is_file() and
                    common.digest(active_base) == baseline[rel]['sha256']):
                candidates.append(active_base)
            saved_quest_normalization = any(p.is_file() and not p.is_symlink() and
                quest_semantics(p) == quest_semantics(actual[rel]) for p in candidates)
        if old_sha is None or old_sha in bases or saved_quest_normalization:
            operations.append({'path': rel, 'action': 'write', 'beforeSha256': old_sha,
                               'afterSha256': target_sha, 'bytes': item['source'].stat().st_size})
            if saved_quest_normalization:
                preserved.append({'path': rel, 'reason': 'live FTB serialization differs only in defaults/icons/chapter order; merged semantic content retained'})
        elif target_sha in bases:
            final[rel] = {'source': actual[rel], 'origin': 'preserved live server edit'}
            preserved.append({'path': rel, 'reason': 'only live server changed', 'sha256': old_sha})
        else:
            conflicts.append({'path': rel, 'liveSha256': old_sha, 'desiredSha256': target_sha,
                              'knownBaseSha256': sorted(bases)})
    for rel, path in sorted(actual.items()):
        if rel in selected:
            continue
        reason = excluded(rel, fixtures)
        delete = False
        if rel.startswith('mods/') and path.suffix == '.jar':
            ids = server_tools.jar_mod_ids(path)
            delete = bool(ids & desired_ids) or server_tools.is_removed(path.name, ids, policy)
            delete = delete or (rel in baseline and snapshot[rel]['sha256'] in ancestors(rel))
        elif not reason and rel in baseline and not (release / 'staging' / rel).exists():
            delete = True
        if delete:
            if snapshot[rel]['sha256'] not in ancestors(rel):
                conflicts.append({'path': rel, 'liveSha256': snapshot[rel]['sha256'],
                                  'reason': 'obsolete path has unreviewed live changes'})
            else:
                operations.append({'path': rel, 'action': 'move_to_backup',
                                   'beforeSha256': snapshot[rel]['sha256'], 'afterSha256': None, 'bytes': 0})
        else:
            preserved.append({'path': rel, 'reason': reason or 'live-only server addition',
                              'sha256': snapshot[rel]['sha256']})
            parts = common.relative_path(rel).parts
            # Existing server client_scripts and actual production controls are
            # retained byte-for-byte in full replacements. Test/exports stay out.
            generated = set(parts) & (SKIP_PARTS - {'client_scripts'})
            fixture = parts[-1] in fixtures or parts[-1] == 'UpstreamMachineSelectionAudit.js'
            probe = parts[-1] in {'probejs.json', 'probe-settings.json'}
            if not generated and not fixture and not probe and not transient_path(rel):
                final[rel] = {'source': path, 'origin': 'preserved captured production file'}
    return ({'schemaVersion': 1, 'packageId': manifest['packageId'],
             'snapshotSha256': common.digest(snapshot_path), 'liveSnapshot': str(live),
             'operations': sorted(operations, key=lambda r: r['path']), 'preserved': preserved, 'conflicts': conflicts,
             'omittedTransientFiles': [{'path': rel, 'sha256': snapshot[rel]['sha256'],
                                        'reason': 'Spark runtime temporary cache'} for rel in actual if transient_path(rel)],
             'conflictPolicy': 'Refuse unknown overlapping edits; require remote beforeSHA before any operation.',
             'rollbackRule': 'Rename original roots into a full backup before extraction; never delete originals; restore exact saved roots for rollback.',
             'summary': {'writes': sum(r['action'] == 'write' for r in operations),
                         'movesToBackup': sum(r['action'] == 'move_to_backup' for r in operations),
                         'writeBytes': sum(r['bytes'] for r in operations), 'preserved': len(preserved), 'conflicts': len(conflicts)}}, final)


def refresh_files(manifest, selected):
    rows = [{'path': rel, 'sha256': common.digest(row['source']), 'bytes': row['source'].stat().st_size,
             'origin': row['origin']} for rel, row in sorted(selected.items())]
    manifest['files'] = rows
    manifest['runtimeSha256'] = tree_hash(rows)
    manifest['runtimeRoots'] = sorted({r['path'].split('/')[0] for r in rows})
    manifest['directoryHashes'] = {root: {'sha256': tree_hash([r for r in rows if r['path'].startswith(root + '/')]),
                                         'files': sum(r['path'].startswith(root + '/') for r in rows)}
                                   for root in manifest['runtimeRoots']}
    manifest['summary']['files'] = len(rows)
    manifest['summary']['runtimeBytes'] = sum(r['bytes'] for r in rows)
    existing_mods = {r['file']: r for r in manifest['mods']}
    final_mods, providers = [], {}
    for rel, item in selected.items():
        if not rel.startswith('mods/') or not rel.endswith('.jar'):
            continue
        name, source = Path(rel).name, item['source']
        row = dict(existing_mods.get(name, {}))
        if not row:
            metadata = jar_metadata(source)
            row = {'file': name, 'modIds': sorted({i for r in metadata if not r['nested'] for i in r['ids']}),
                   'embeddedModIds': sorted({i for r in metadata if r['nested'] for i in r['ids']}),
                   'preservedLiveOnly': True}
        row.update({'sha256': common.digest(source), 'bytes': source.stat().st_size})
        for mod_id in row['modIds']:
            if mod_id in providers:
                raise common.PatchError('Preserved server addition conflicts with new mod ID: ' + mod_id)
            providers[mod_id] = name
        final_mods.append(row)
    manifest['mods'] = sorted(final_mods, key=lambda r: r['file'])
    manifest['summary']['serverMods'] = len(final_mods)
    for rel, expected in manifest.get('protectedCatalogs', {}).items():
        if rel not in selected or common.digest(selected[rel]['source']) != expected:
            raise common.PatchError('Live catalog conflicts with protected merged catalog: ' + rel)


def control_path(rel):
    return any(rel == p.rstrip('/') or rel.startswith(p if p.endswith('/') else p + '/') for p in PRESERVE_REMOTE)


def refresh_controls(selected, manifest, refresh_root, release):
    """Accept a stopped config+kubejs snapshot, only changing live controls."""
    refresh_root = Path(refresh_root).absolute()
    if not (refresh_root / 'config').is_dir() or not (refresh_root / 'kubejs/config').is_dir():
        raise common.PatchError('Control refresh requires complete stopped-server config and kubejs directories')
    old = common.read_json(Path(release) / 'evidence/live-before-manifest.json')['files']
    incoming = {p.relative_to(refresh_root).as_posix(): p for p in files(refresh_root)}
    conflicts = []
    for rel, path in incoming.items():
        if rel.split('/')[0] not in ('config', 'kubejs'):
            raise common.PatchError('Unexpected root in control refresh: ' + rel)
        if set(Path(rel).parts) & {'exported', 'probe', 'logs', '.DS_Store'}:
            continue
        if transient_path(rel):
            continue
        if not control_path(rel) and common.digest(path) != old.get(rel, {}).get('sha256'):
            conflicts.append(rel)
    for rel in old:
        if rel.startswith(('config/', 'kubejs/')) and rel not in incoming and not control_path(rel) and not transient_path(rel):
            if not set(Path(rel).parts) & {'exported', 'probe', 'logs', '.DS_Store'}:
                conflicts.append(rel + ' (missing)')
    if conflicts:
        raise common.PatchError('Stopped snapshot contains non-control changes; review before packaging: ' + repr(conflicts))
    removed, copied = [], []
    omitted = {row['path']: row for row in manifest.get('omittedTransientFiles', [])}
    for rel in list(selected):
        if transient_path(rel):
            selected.pop(rel)
            continue
        if control_path(rel) and rel not in incoming:
            selected.pop(rel)
            removed.append(rel)
    for rel, path in incoming.items():
        if control_path(rel):
            selected[rel] = {'source': path, 'origin': 'stopped live control/state refresh'}
            copied.append({'path': rel, 'sha256': common.digest(path), 'bytes': path.stat().st_size})
    for rel in set(old) | set(incoming):
        if transient_path(rel):
            omitted[rel] = {'path': rel, 'reason': 'Spark volatile runtime cache; additions/deletions ignored',
                            'capturedSha256': old.get(rel, {}).get('sha256'),
                            'stoppedSha256': common.digest(incoming[rel]) if rel in incoming else None}
    manifest['omittedTransientFiles'] = sorted(omitted.values(), key=lambda row: row['path'])
    manifest['stoppedControlRefresh'] = {'root': str(refresh_root), 'files': copied,
                                         'absentAfterStop': removed, 'nonControlChanges': []}


def write_archive(output, selected, manifest, delta=None, delta_only=False):
    name = 'server-payload' if delta_only else 'server-runtime'
    rows = [r for r in delta['operations'] if r['action'] == 'write'] if delta_only else manifest['files']
    temporary = Path(tempfile.mkdtemp(prefix='.' + name + '-', dir=output))
    try:
        payload = temporary / name
        payload.mkdir()
        for rel in manifest.get('runtimeRequiredDirectories', REQUIRED_DIRS):
            (payload / rel).mkdir(parents=True, exist_ok=True)
        for row in rows:
            target = payload / row['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(selected[row['path']]['source'], target)
            if common.digest(target) != row.get('afterSha256', row.get('sha256')):
                raise common.PatchError('Source changed during build: ' + row['path'])
        common.write_json(temporary / 'server-runtime-manifest.json', manifest)
        if delta:
            common.write_json(temporary / 'server-delta-manifest.json', delta)
        archive = temporary / (name + '.zip')
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for rel in manifest.get('runtimeRequiredDirectories', REQUIRED_DIRS):
                z.write(payload / rel, rel.rstrip('/') + '/')
            for row in rows:
                z.write(payload / row['path'], row['path'])
            z.write(temporary / 'server-runtime-manifest.json', 'server-runtime-manifest.json')
            if delta:
                z.write(temporary / 'server-delta-manifest.json', 'server-delta-manifest.json')
        with zipfile.ZipFile(archive) as z:
            if z.testzip() is not None:
                raise common.PatchError('Server ZIP integrity failed')
        destination = output / name
        if destination.exists():
            if destination.is_symlink() or not destination.is_dir():
                raise common.PatchError('Unsafe previous package output')
            shutil.rmtree(destination)
        shutil.move(str(payload), destination)
        for file in ('server-runtime-manifest.json', 'server-delta-manifest.json'):
            if (temporary / file).exists():
                shutil.copy2(temporary / file, output / file)
        shutil.move(str(archive), output / archive.name)
        return {'archive': str(output / archive.name), 'sha256': common.digest(output / archive.name),
                'bytes': (output / archive.name).stat().st_size}
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def describe_controls(manifest, selected):
    controls = []
    for rel, row in selected.items():
        if not control_path(rel):
            continue
        entry = {'path': rel, 'sha256': common.digest(row['source']), 'origin': row['origin']}
        if rel.endswith('.json'):
            value = common.read_json(row['source'])
            entry['controlSummary'] = {k: value[k] for k in ('armed', 'enabled', 'worldName', 'resetId',
                                                             'terminal', 'updatedAt', 'centerX', 'centerZ') if k in value}
        controls.append(entry)
    manifest['preservedControlFiles'] = controls
    manifest['controlStateDeploymentCheck'] = 'Full archive includes captured production values, never validation fixture controls. Stop server and refresh config+kubejs controls; compare these hashes before/after extraction. Retain original root directories as backup.'


def build(release, staging=None, validation=None, output=None, validation_reports=(), check=False,
          live_before=None, server=SERVER, prepare_runtime=False, live_controls_refresh=None):
    release = Path(release).absolute()
    output = Path(output).absolute() if output else release
    if not validation_reports and not check and not prepare_runtime:
        raise common.PatchError('Final server build requires passing --validation-report files; use --check for plans only.')
    reports = []
    for path in validation_reports:
        path = Path(path).absolute()
        if common.read_json(path).get('passed') is not True:
            raise common.PatchError('Validation report has not passed: ' + str(path))
        reports.append({'path': str(path), 'sha256': common.digest(path), 'passed': True})
    selected, manifest = plan(release, staging, validation, server)
    manifest.update({'validationReports': reports, 'validationStatus': 'review_only' if check or prepare_runtime else 'validated'})
    delta = None
    if live_before:
        delta, selected = delta_plan(selected, manifest, live_before, release, server)
        delta.update({'validationReports': reports, 'validationStatus': manifest['validationStatus']})
        common.write_json(release / 'evidence/server-delta-plan.json', delta)
        refresh_files(manifest, selected)
        manifest['liveSnapshotSha256'] = delta['snapshotSha256']
        manifest['preservedCapturedProductionFiles'] = delta['preserved']
        manifest['omittedTransientFiles'] += delta['omittedTransientFiles']
    if live_controls_refresh:
        if not live_before:
            raise common.PatchError('Stopped control refresh requires --live-before ancestry')
        refresh_controls(selected, manifest, live_controls_refresh, release)
        refresh_files(manifest, selected)
    describe_controls(manifest, selected)
    tested_root = Path(validation).absolute() if validation else release / 'validation'
    all_differences, critical_differences = [], []
    for rel, row in selected.items():
        if same_runtime(row['source'], tested_root / rel, rel):
            continue
        difference = {'path': rel, 'origin': row['origin'], 'sha256': common.digest(row['source'])}
        all_differences.append(difference)
        if critical_path(rel):
            critical_differences.append(difference)
    manifest['differencesFromValidation'] = critical_differences
    manifest['allDifferencesFromValidation'] = all_differences
    common.write_json(release / 'evidence/server-package-plan.json', manifest)
    if prepare_runtime:
        if delta and delta['conflicts']:
            raise common.PatchError('Resolve live conflicts before preparing a test runtime mirror')
        output.mkdir(parents=True, exist_ok=True)
        mirror = output / 'server-runtime-review'
        if mirror.exists():
            if mirror.is_symlink() or not mirror.is_dir():
                raise common.PatchError('Unsafe existing runtime review mirror')
            shutil.rmtree(mirror)
        for rel, row in selected.items():
            target = mirror / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(row['source'], target)
        for rel in manifest.get('runtimeRequiredDirectories', REQUIRED_DIRS):
            (mirror / rel).mkdir(parents=True, exist_ok=True)
        common.write_json(output / 'server-runtime-review-manifest.json', manifest)
        return {'passed': True, 'reviewOnly': True, 'mirror': str(mirror),
                'differencesFromValidation': critical_differences,
                **manifest['summary'], **({'delta': delta['summary']} if delta else {})}
    if check:
        return {'passed': (not delta or not delta['conflicts']) and not manifest['differencesFromValidation'],
                'checkOnly': True, **manifest['summary'], 'runtimeDifferences': len(manifest['differencesFromValidation']),
                **({'delta': delta['summary']} if delta else {})}
    if delta and delta['conflicts']:
        raise common.PatchError('Overlapping live changes require resolution; see evidence/server-delta-plan.json')
    if manifest['differencesFromValidation']:
        raise common.PatchError('Merged runtime differs from validation; prepare and validate again before building')
    output.mkdir(parents=True, exist_ok=True)
    archives = [write_archive(output, selected, manifest, delta)]
    if delta:
        archives.append(write_archive(output, selected, manifest, delta, delta_only=True))
    result = {'passed': True, 'archives': archives, 'runtimeSha256': manifest['runtimeSha256'],
              **manifest['summary'], **({'delta': delta['summary']} if delta else {})}
    common.write_json(release / 'evidence/server-package-build.json', result)
    return result


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--release', type=Path, default=HERE)
    cli.add_argument('--staging', type=Path)
    cli.add_argument('--validation', type=Path)
    cli.add_argument('--output', type=Path)
    cli.add_argument('--live-before', type=Path)
    cli.add_argument('--validation-report', type=Path, action='append', default=[])
    cli.add_argument('--check', action='store_true')
    cli.add_argument('--prepare-runtime', action='store_true', help='Write a review-only runtime mirror for coldboot; no archive or deploy')
    cli.add_argument('--live-controls-refresh', type=Path, help='Complete stopped config+kubejs snapshot; only control/state changes may differ')
    args = cli.parse_args()
    print(json.dumps(build(args.release, args.staging, args.validation, args.output,
                           args.validation_report, args.check, args.live_before,
                           prepare_runtime=args.prepare_runtime, live_controls_refresh=args.live_controls_refresh), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (common.PatchError, OSError, ValueError, KeyError, zipfile.BadZipFile) as error:
        raise SystemExit(str(error))
