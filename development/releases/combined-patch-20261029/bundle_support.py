"""Portable planning helpers for the combined client patch (standard library)."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import zipfile

PACK = 'Expedition-HNN-v18-Resource-Only-1.20.1.zip'
SETTINGS = frozenset(('options.txt', 'config/paxi/resourcepack_load_order.json'))


def retire_name(value):
    value = value[5:] if value.startswith('file/') else value
    return ((value.startswith('Expedition-HNN-') and value != PACK)
            or value.startswith('expedition-hnn-gui-')
            or value in ('mod:expedition_hnn_gui', 'expedition_hnn_gui'))


def order(values):
    if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
        raise ValueError('Resource pack order must be a list of strings')
    return [v for v in values if not retire_name(v)
            and v not in (PACK, 'file/' + PACK)] + [PACK]


def generated(rel, before, after):
    sha = lambda raw: hashlib.sha256(raw).hexdigest() if raw is not None else None
    return {'path': rel, 'action': 'write' if after is not None else 'delete',
            'beforeSha256': sha(before), 'afterSha256': sha(after),
            'observedSha256': sha(before), 'bytes': len(after or b''),
            'generatedHex': after.hex() if after is not None else None, 'state': 'pending'}


def prepare(root, package, manifest, core):
    """Plan the 10/28 prerequisite and HNN migration without writing the instance."""
    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec = importlib.util.spec_from_file_location('expedition_prerequisite', package / 'prerequisite/install.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Existing reviewed recipe merger adds only absent independent IDs.
        prerequisite = module.load_bundle()
        jobs, _ = module.make_plan(root, 'client', prerequisite)
    except module.Conflict as error:
        raise core.PatchError(str(error)) from error
    finally:
        sys.dont_write_bytecode = old
    operations = [generated(j['path'], j['before'], j['after'])
                  for j in jobs if j['before'] != j['after']]
    for rel, expected in manifest.get('requiredFiles', {}).items():
        if core.current_hash(root, rel) != expected:
            raise core.PatchError('Missing/incompatible tested base dependency: ' + rel)
    known = manifest['retiredFiles']
    for folder in ('mods', 'resourcepacks', 'config/paxi/resourcepacks'):
        directory = root / folder
        if directory.is_symlink() or not directory.is_dir():
            raise core.PatchError('Expected real client directory: ' + folder)
        for path in sorted(directory.iterdir()):
            if not retire_name(path.name):
                continue
            rel = path.relative_to(root).as_posix()
            observed = core.current_hash(root, rel)
            if observed not in known.get(rel, []):
                raise core.PatchError('Unknown old HNN file; preserved without changes: ' + rel)
            operations.append(generated(rel, path.read_bytes(), None))
    for rel in sorted(SETTINGS):
        path = core.safe_path(root, rel)
        if not path.is_file():
            raise core.PatchError('Expected existing client setting: ' + rel)
        raw = path.read_bytes()
        text = raw.decode('utf-8')
        if rel == 'options.txt':
            lines = text.splitlines(keepends=True)
            matches = [i for i, line in enumerate(lines) if line.startswith('resourcePacks:')]
            if len(matches) != 1:
                raise core.PatchError('Expected exactly one resourcePacks line in options.txt')
            index = matches[0]
            old_line = lines[index]
            values = json.loads(old_line.split(':', 1)[1])
            wanted = order(values)
            if wanted == values:
                continue
            newline = '\r\n' if old_line.endswith('\r\n') else '\n' if old_line.endswith('\n') else ''
            lines[index] = 'resourcePacks:' + json.dumps(wanted, ensure_ascii=False, separators=(',', ':')) + newline
            updated = ''.join(lines).encode('utf-8')
        else:
            document = json.loads(text)
            if not isinstance(document, dict) or 'loadOrder' not in document:
                raise core.PatchError('Expected Paxi loadOrder object')
            wanted = order(document['loadOrder'])
            if wanted == document['loadOrder']:
                continue
            document['loadOrder'] = wanted
            updated = (json.dumps(document, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        operations.append(generated(rel, raw, updated))
    return operations


def mod_ids(path):
    try:
        with zipfile.ZipFile(path) as archive:
            text = archive.read('META-INF/mods.toml').decode('utf-8')
    except (KeyError, zipfile.BadZipFile, UnicodeError):
        return set()
    found, in_mod = set(), False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('['):
            in_mod = bool(re.fullmatch(r'\[\[mods\]\]\s*(?:#.*)?', stripped))
        elif in_mod:
            match = re.match(r'\s*modId\s*=\s*[\"\x27]([^\"\x27]+)[\"\x27]', line)
            if match:
                found.add(match.group(1))
    return found


def check_duplicates(root, package, operations, core):
    inventory = {p.relative_to(root).as_posix(): p for p in (root / 'mods').glob('*.jar')}
    changed = set()
    for op in operations:
        if not op['path'].startswith('mods/'):
            continue
        inventory.pop(op['path'], None)
        if op['action'] == 'write':
            source = core.safe_path(package / 'client-payload', op['path'])
            inventory[op['path']] = source
            changed.update(mod_ids(source))
    found = {}
    for rel, path in sorted(inventory.items()):
        core.safe_path(root, rel)
        for mod_id in mod_ids(path) & changed:
            found.setdefault(mod_id, []).append(rel)
    duplicates = {key: value for key, value in found.items() if len(value) > 1}
    if duplicates:
        raise core.PatchError('Duplicate mod IDs in projected client; no changes made:\n' + json.dumps(duplicates, indent=2))


def authorized_extra(rel, package):
    # Only the original prerequisite's explicit paths, the two settings files,
    # and the shipped HNN retirement whitelist may enter a transaction.
    original = json.loads((package / 'prerequisite/manifest.json').read_text(encoding='utf-8'))
    manifest = json.loads((package / 'client-manifest.json').read_text(encoding='utf-8'))
    return rel in SETTINGS or rel == 'kubejs/config/expedition-selected-native-recipes.json' or rel == 'config/quark-common.toml' or rel in {r['path'] for r in original['payload']} or rel in manifest['retiredFiles']
