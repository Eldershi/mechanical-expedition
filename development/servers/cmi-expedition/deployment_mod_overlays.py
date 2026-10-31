"""Strict, manifest-authorized dedicated-server overlays and additive compatibility mods."""
from pathlib import Path
import hashlib
import json
import re
import io
import tomllib
import zipfile


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def load_server_additions(root):
    """Keep reviewed server-only compatibility jars across future client rebuilds."""
    root = Path(root)
    manifest_path = root / 'deployment/server-additions.json'
    directory = root / 'deployment/server-additions'
    if not manifest_path.is_file():
        if directory.exists() and list(directory.glob('*.jar')):
            raise ValueError('Server additions exist without a manifest')
        return {}
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('schemaVersion') != 1 or not isinstance(manifest.get('mods'), list):
        raise ValueError('Unsupported server addition manifest')
    additions = {}
    ids = set()
    for row in manifest['mods']:
        name = row['file']
        if not isinstance(name, str) or Path(name).name != name or '\\' in name or not name.endswith('.jar'):
            raise ValueError('Invalid server addition filename')
        if name in additions or not row.get('patchId'):
            raise ValueError('Duplicate or unidentified server addition: ' + name)
        expected = row.get('sha256')
        if not isinstance(expected, str) or re.fullmatch('[0-9a-f]{64}', expected) is None:
            raise ValueError('Invalid server addition hash: ' + name)
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or symbolic server addition: ' + name)
        blob = path.read_bytes()
        if digest(blob) != expected:
            raise ValueError('Server addition bytes do not match manifest: ' + name)
        with zipfile.ZipFile(io.BytesIO(blob)) as jar:
            info = tomllib.loads(jar.read('META-INF/mods.toml').decode())
        mod_ids = sorted(mod['modId'] for mod in info.get('mods', []))
        if not mod_ids or mod_ids != sorted(row.get('modIds', [])) or ids.intersection(mod_ids):
            raise ValueError('Server addition mod IDs differ or conflict: ' + name)
        ids.update(mod_ids)
        additions[name] = {**row, 'path': path, 'blob': blob}
    for path in directory.glob('*.jar'):
        if path.name not in additions:
            raise ValueError('Unregistered server addition: ' + path.name)
    return additions


def load_mod_overlays(root):
    root = Path(root)
    manifest = json.loads((root / 'deployment/server-patches.json').read_text())
    if manifest.get('schemaVersion') != 1 or not isinstance(manifest.get('mods'), list):
        raise ValueError('Unsupported server patch manifest')
    directory = root / 'deployment/mods'
    overlays = {}
    for row in manifest['mods']:
        name = row['file']
        if not isinstance(name, str) or Path(name).name != name or '\\' in name or not name.endswith('.jar'):
            raise ValueError('Invalid overlay filename')
        if name in overlays:
            raise ValueError('Duplicate overlay filename: ' + name)
        if not row.get('patchId'):
            raise ValueError('Overlay has no patch identifier: ' + name)
        for key in ('upstreamSha256', 'patchedSha256'):
            if not isinstance(row.get(key), str) or re.fullmatch('[0-9a-f]{64}', row[key]) is None:
                raise ValueError('Invalid overlay hash: ' + name)
        path = directory / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Missing or symbolic overlay: ' + name)
        blob = path.read_bytes()
        if digest(blob) != row['patchedSha256']:
            raise ValueError('Overlay bytes do not match manifest: ' + name)
        overlays[name] = {**row, 'path': path, 'blob': blob}
    for path in directory.glob('*.jar'):
        if path.name not in overlays:
            raise ValueError('Unregistered mod overlay: ' + path.name)
    return overlays


def apply_mod_overlay(target, entry, overlays):
    """Called only after prepare copies an upstream client mod to its server target."""
    target = Path(target)
    overlay = overlays.get(target.name)
    if overlay is None:
        return
    if entry['file'] != target.name or entry['sha256'] != overlay['upstreamSha256']:
        raise ValueError('Client selection is not the reviewed upstream mod: ' + target.name)
    if digest(target.read_bytes()) != overlay['upstreamSha256']:
        raise ValueError('Prepare target is not the reviewed upstream mod: ' + target.name)
    target.write_bytes(overlay['blob'])
    entry['upstreamSha256'] = overlay['upstreamSha256']
    entry['sha256'] = overlay['patchedSha256']
    entry['patch'] = 'deployment/server-patches.json: ' + overlay['patchId']


def source_for_mod_package(original, selected_sha256, overlays):
    """Accept the reviewed upstream or prepared state, then package the reviewed overlay."""
    original = Path(original)
    overlay = overlays.get(original.name)
    if overlay is None:
        return original
    known = {overlay['upstreamSha256'], overlay['patchedSha256']}
    if selected_sha256 not in known or digest(original.read_bytes()) not in known:
        raise ValueError('Unknown source or selection hash for overlaid mod: ' + original.name)
    return overlay['path']
