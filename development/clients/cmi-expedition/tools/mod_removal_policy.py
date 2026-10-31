"""Enforce persistent removals and explicit later additions without changing history."""
from pathlib import Path
import hashlib
import io
import json
import re
import tomllib
import zipfile


def _filename(name):
    if not isinstance(name, str) or Path(name).name != name or '\\' in name or not name.endswith('.jar'):
        raise ValueError('Invalid mod filename in removal policy: ' + str(name))
    return name


def load_removal_policy(client_root):
    path = Path(client_root) / 'mod-removal-20261018.json'
    blob = path.read_bytes()
    policy = json.loads(blob)
    if policy.get('schemaVersion') != 1 or not isinstance(policy.get('removed'), list):
        raise ValueError('Unsupported mod removal policy')
    files, ids = set(), set()
    for row in policy['removed']:
        name = _filename(row['file'])
        if name in files:
            raise ValueError('Duplicate removed mod filename: ' + name)
        files.add(name)
        declared = row.get('modIds')
        if not isinstance(declared, list) or not declared or any(not isinstance(v, str) or not v for v in declared):
            raise ValueError('Missing removed mod IDs: ' + name)
        if len(set(declared)) != len(declared) or ids.intersection(declared):
            raise ValueError('Duplicate removed mod ID: ' + name)
        ids.update(declared)
        if re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')) is None:
            raise ValueError('Invalid removed mod hash: ' + name)
    additions = policy.get('approvedAdditions', [])
    if not isinstance(additions, list):
        raise ValueError('Approved additions must be a list')
    addition_files, addition_ids = {}, set()
    for row in additions:
        if not isinstance(row, dict):
            raise ValueError('Invalid approved addition')
        name = _filename(row.get('file'))
        declared = row.get('modIds')
        if name in addition_files or name in files:
            raise ValueError('Duplicate or removed approved addition filename: ' + name)
        if not isinstance(declared, list) or not declared or any(not isinstance(v, str) or not v for v in declared):
            raise ValueError('Missing approved addition mod IDs: ' + name)
        if len(set(declared)) != len(declared) or (ids | addition_ids).intersection(declared):
            raise ValueError('Duplicate or removed approved addition mod ID: ' + name)
        if re.fullmatch('[0-9a-f]{64}', row.get('sha256', '')) is None:
            raise ValueError('Invalid approved addition hash: ' + name)
        addition_files[name] = row
        addition_ids.update(declared)
    expected = policy.get('expectedClientModCount')
    baseline = policy.get('baselineClientModCount')
    if (type(expected) is not int or expected <= 0 or type(baseline) is not int
            or baseline + len(addition_files) - len(files) != expected):
        raise ValueError('Removal policy mod counts do not reconcile')
    expected_files = policy.get('expectedClientFiles')
    if not isinstance(expected_files, list) or len(expected_files) != expected:
        raise ValueError('Removal policy must enumerate the current client mod set')
    expected_files = [_filename(name) for name in expected_files]
    if (len(set(expected_files)) != expected or files.intersection(expected_files)
            or not set(addition_files).issubset(expected_files)):
        raise ValueError('Removal policy current client mod set is inconsistent')
    retained = policy.get('retainedModIds')
    if not isinstance(retained, list) or not retained or any(not isinstance(v, str) or not v for v in retained) or ids.intersection(retained):
        raise ValueError('Removal policy retained mod IDs are inconsistent')
    return {**policy, 'removedFiles': files, 'removedIds': ids,
            'additionFiles': addition_files, 'additionIds': addition_ids,
            'expectedFiles': set(expected_files), 'sha256': hashlib.sha256(blob).hexdigest()}


def jar_mod_ids(source):
    """Inspect metadata, including embedded providers; never initialize a mod class."""
    if isinstance(source, (str, Path)):
        path = Path(source)
        if path.is_symlink() or not path.is_file():
            raise ValueError('Mod source is missing or symbolic: ' + str(path))
        with zipfile.ZipFile(path) as archive:
            return _archive_ids(archive)
    with zipfile.ZipFile(io.BytesIO(source)) as archive:
        return _archive_ids(archive)


def _archive_ids(archive):
    ids = set()
    names = set(archive.namelist())
    if 'META-INF/mods.toml' in names:
        metadata = tomllib.loads(archive.read('META-INF/mods.toml').decode('utf-8-sig'))
        ids.update(row['modId'] for row in metadata.get('mods', []))
    if 'META-INF/jarjar/metadata.json' in names:
        for row in json.loads(archive.read('META-INF/jarjar/metadata.json')).get('jars', []):
            if row['path'] in names:
                ids.update(jar_mod_ids(archive.read(row['path'])))
    return ids


def is_removed(name, ids, policy):
    return name in policy['removedFiles'] or bool(set(ids) & policy['removedIds'])


def assert_mod_allowed(name, ids, policy):
    _filename(name)
    if is_removed(name, ids, policy):
        raise ValueError('Mod excluded by the user removal policy: ' + name)


def validate_mod_rows(rows, policy, *, client=False):
    names, provided = set(), set()
    for row in rows:
        name = row['file']
        ids = set(row['modIds'])
        assert_mod_allowed(name, ids, policy)
        addition = policy.get('additionFiles', {}).get(name)
        if addition is not None:
            if not set(addition['modIds']).issubset(ids):
                raise ValueError('Approved addition mod IDs do not match: ' + name)
            # Metadata-only callers retain their existing contract; callers with
            # bytes or selection hashes also verify the approved artifact.
            if 'sha256' in row and row['sha256'] != addition['sha256']:
                raise ValueError('Approved addition checksum mismatch: ' + name)
        if name in names:
            raise ValueError('Duplicate mod filename: ' + name)
        names.add(name)
        provided.update(ids)
    if client:
        if len(names) != policy['expectedClientModCount'] or names != policy['expectedFiles']:
            raise ValueError('Current client mod set differs from the reviewed removal policy: '
                             + repr({'count': len(names), 'missing': sorted(policy['expectedFiles'] - names),
                                     'unexpected': sorted(names - policy['expectedFiles'])}))
        missing_ids = set(policy['retainedModIds']) - provided
        if missing_ids:
            raise ValueError('Explicitly retained mods are missing: ' + repr(sorted(missing_ids)))
    return {'modCount': len(names), 'removalPolicySha256': policy['sha256']}


def validate_client_mods(paths, policy):
    rows = []
    for source in paths:
        path = Path(source)
        row = {'file': path.name, 'modIds': jar_mod_ids(path)}
        if path.name in policy.get('additionFiles', {}):
            row['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows.append(row)
    return validate_mod_rows(rows, policy, client=True)
