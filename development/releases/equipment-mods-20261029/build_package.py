#!/usr/bin/env python3
"""Build the small, additive equipment update from reviewed payload files."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    manifest_path = ROOT / 'client-manifest.json'
    manifest = json.loads(manifest_path.read_text())
    old = {row['path']: row for row in manifest['operations']}
    rows = []
    for path in sorted((ROOT / 'client-payload').rglob('*')):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT / 'client-payload').as_posix()
        rows.append({'path': rel, 'action': 'write',
                     'beforeSha256': old.get(rel, {}).get('beforeSha256'),
                     'afterSha256': sha(path), 'bytes': path.stat().st_size})
    manifest['operations'] = rows
    manifest['summary'] = {'writes': len(rows), 'deletes': 0,
                           'payloadBytes': sum(row['bytes'] for row in rows)}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    server = {**manifest, 'target': 'dedicated-server',
              'installMode': 'additive-only; stop server before extracting',
              'preserves': ['existing mods', 'custom recipes', 'parallel recipe catalogs',
                            'world', 'existing configuration']}
    server_path = ROOT / 'expedition-equipment-install-20261029.json'
    server_path.write_text(json.dumps(server, ensure_ascii=False, indent=2) + '\n')
    with ZipFile(ROOT / 'equipment-server-additions-20261029.zip', 'w', ZIP_DEFLATED) as archive:
        for row in rows:
            archive.write(ROOT / 'client-payload' / row['path'], row['path'])
        archive.write(server_path, server_path.name)
    with ZipFile(ROOT / 'equipment-client-update-20261029.zip', 'w', ZIP_DEFLATED) as archive:
        for row in rows:
            archive.write(ROOT / 'client-payload' / row['path'], 'client-payload/' + row['path'])
        for name in ('client-manifest.json', 'install_client.py', 'README.md'):
            archive.write(ROOT / name, name)
    print(json.dumps({'writes': len(rows), 'deletes': 0,
                      'archives': [{'name': name, 'sha256': sha(ROOT / name),
                                    'bytes': (ROOT / name).stat().st_size}
                                   for name in ('equipment-server-additions-20261029.zip',
                                                'equipment-client-update-20261029.zip')]}, indent=2))


if __name__ == '__main__':
    build()
