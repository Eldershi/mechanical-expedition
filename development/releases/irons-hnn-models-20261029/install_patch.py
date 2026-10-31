#!/usr/bin/env python3
"""Install only this release's additive payload, backing up any existing files."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent
ACTIVE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--active-client', action='store_true')
    args = parser.parse_args()
    files = sorted(p for p in (ROOT / 'payload').rglob('*') if p.is_file())
    assert len(files) == 13, [str(p) for p in files]
    records = []
    targets = [('active-client', ACTIVE)] if args.active_client else [
        ('server-instance', PROJECT / 'servers/cmi-expedition/instance'),
        ('server-deployment', PROJECT / 'servers/cmi-expedition/deployment'),
        ('client-overlay', PROJECT / 'clients/cmi-expedition/overlay'),
    ]
    for label, target in targets:
        for source in files:
            relative = source.relative_to(ROOT / 'payload')
            dest = target / relative
            before = sha(dest) if dest.exists() else None
            expected = sha(source)
            if before is not None and before != expected:
                backup = ROOT / 'backups' / label / relative
                if backup.exists():
                    raise RuntimeError('Existing backup; inspect before replacing: ' + str(backup))
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest, backup)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            assert sha(dest) == expected
            records.append({'target': label, 'path': str(relative), 'beforeSha256': before, 'sha256': expected})
    receipt = {'installedAtUtc': datetime.now(timezone.utc).isoformat(), 'files': records}
    name = 'active-client-install-receipt.json' if args.active_client else 'workspace-install-receipt.json'
    (ROOT / name).write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    if not args.active_client:
        archive = ROOT / 'expedition-irons-hnn-models-20261029.zip'
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            for source in files:
                z.write(source, source.relative_to(ROOT / 'payload'))
        print(json.dumps({'fileCount': len(files), 'archive': str(archive), 'sha256': sha(archive)}, ensure_ascii=False))
    print(json.dumps({'receipt': name, 'verifiedCopies': len(records)}))


if __name__ == '__main__':
    main()
