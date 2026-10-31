"""Apply the reviewed 2026-10-18 removal decision to one instance, preserving jars."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'mod-removal-20261018.json'
RAILWAY_PATCH = '2eb15f85b669104c485999984e2cabc45210bb436b5a86092b7c8339cf5449ce'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply(instance, backup, report, allow_server_patches=False):
    policy = json.loads(MANIFEST.read_text())
    assert policy['schemaVersion'] == 1 and len(policy['removed']) == 10
    instance, backup, report = Path(instance).resolve(), Path(backup).resolve(), Path(report).resolve()
    assert instance.is_dir() and (instance / 'mods').is_dir(), instance
    plan = []
    for row in policy['removed']:
        name = row['file']
        assert Path(name).name == name and name.endswith('.jar') and '\\' not in name
        source, target = instance / 'mods' / name, backup / 'mods' / name
        assert not source.is_symlink() and not target.is_symlink()
        if not source.exists():
            plan.append({'file': name, 'state': 'already_absent', 'backupExists': target.is_file()})
            continue
        actual = digest(source)
        allowed = {row['sha256']}
        if allow_server_patches and 'railway_automation' in row['modIds']:
            allowed.add(RAILWAY_PATCH)
        assert actual in allowed, ('Unreviewed jar bytes', source, actual)
        if target.exists():
            assert digest(target) == actual, ('Backup differs', target)
        plan.append({'file': name, 'state': 'quarantine', 'sha256': actual,
                     'source': str(source), 'backup': str(target), 'modIds': row['modIds']})
    # Validate the complete plan before changing any directory.
    for row in plan:
        if row['state'] != 'quarantine':
            continue
        source, target = Path(row['source']), Path(row['backup'])
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            source.unlink()  # A verified identical backup already exists.
        else:
            shutil.move(str(source), str(target))
        assert digest(target) == row['sha256'] and not source.exists()
        row['state'] = 'removed_with_backup'
    result = {'at': datetime.now().astimezone().isoformat(), 'instance': str(instance),
              'policy': str(MANIFEST), 'remainingJarCount': len(list((instance / 'mods').glob('*.jar'))),
              'removed': plan, 'worldsChanged': False}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, default=ROOT / 'instance')
    parser.add_argument('--backup-root', type=Path, default=ROOT / 'backups/before-mod-removal-20261018/instance')
    parser.add_argument('--report', type=Path, default=ROOT / 'evidence/mod-removal-20261018/client-jars.json')
    parser.add_argument('--allow-server-patches', action='store_true')
    args = parser.parse_args()
    result = apply(args.instance, args.backup_root, args.report, args.allow_server_patches)
    print(json.dumps({'instance': result['instance'], 'remainingJarCount': result['remainingJarCount'],
                      'removedNow': sum(r['state'] == 'removed_with_backup' for r in result['removed'])}, ensure_ascii=False))


if __name__ == '__main__':
    main()
