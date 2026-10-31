"""Package only the validated server-side mod-removal changes, without worlds."""
from pathlib import Path
from datetime import datetime
import hashlib
import argparse
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
SERVER = PROJECT / 'servers/cmi-expedition'
REVIEW = PROJECT / 'design/current-mod-checklist/removal-20261018'
OUT = PROJECT / 'releases/0.2.0-test.1-mod-removal-20261018'


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validation', type=Path, default=ROOT / 'evidence/mod-removal-20261018/runtime2-validation.json')
    args = parser.parse_args()
    validation = json.loads(args.validation.read_text())
    if validation.get('passed') is not True:
        raise RuntimeError('Post-removal runtime validation must pass before packaging')
    sync = json.loads((REVIEW / 'server-script-sync.json').read_text())
    policy_blob = (ROOT / 'mod-removal-20261018.json').read_bytes()
    policy = json.loads(policy_blob)
    files = {}
    for row in sync['copied']:
        rel = row['path']
        if Path(rel).is_absolute() or '..' in Path(rel).parts or not rel.startswith('kubejs/'):
            raise ValueError('Unexpected patch path: ' + rel)
        blob = (SERVER / 'instance' / rel).read_bytes()
        if sha(blob) != row['sha256']:
            raise RuntimeError('Reviewed source changed: ' + rel)
        files[rel] = blob
    files['mod-removal-20261018.json'] = policy_blob
    files['server-patches.json'] = (SERVER / 'deployment/server-patches.json').read_bytes()
    removed = [dict(row, serverMayAlreadyBeAbsent='interlocked' in row['modIds']) for row in policy['removed']]
    operations = {'schemaVersion': 1, 'removedMods': removed,
                  'moveDataOutOfActiveTree': sync['removed'],
                  'backupDirectory': 'before-mod-removal-20261018',
                  'worldReset': False, 'keepModIds': policy['retainedModIds']}
    files['mod-removal-operations.json'] = (json.dumps(operations, ensure_ascii=False, indent=2) + '\n').encode()
    files['Mod-Removal-README.txt'] = (
        '机械动力：远征 2026-10-18 服务端模组精简补丁\n'
        '先正常停服并备份玩家数据、世界、脚本和模组。\n'
        '按 mod-removal-operations.json 将9个仍在服务端的已删模组移出mods，保留备份。'
        'Interlocked 不作为服务端组件安装。\n'
        '将列出的3个旧兼容data文件移出kubejs/data，再把此包解压到服务端根目录覆盖。\n'
        '保留Rock & Stone、Create、Steam_Rails、Curios、Citadel、GeckoLib，'
        '保留现有CorgiLib/TYG内存修复JAR。\n'
        '本包不含任何存档或JAR，不会自动删除文件；只覆盖已验证的脚本、数据和说明。世界重建另行执行。\n'
        '启动后核对指南29本、迁移审计无缺失、RNS与主线设备配方仍在，最后执行保存。\n'
    ).encode('utf-8-sig')
    manifest = [{'path': name, 'bytes': len(blob), 'sha256': sha(blob)} for name, blob in sorted(files.items())]
    files['mod-removal-payload.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / 'mechanical-expedition-mod-removal-20261018-server.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, blob in sorted(files.items()):
            archive.writestr(name, blob)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for row in manifest:
            assert sha(archive.read(row['path'])) == row['sha256']
        assert not any(name.endswith('.jar') or name.startswith(('world/', 'expedition/')) for name in archive.namelist())
    report = {'builtAt': datetime.now().astimezone().isoformat(), 'file': str(path),
              'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes()),
              'files': manifest, 'dataFilesToMove': sync['removed'],
              'validation': str(args.validation.resolve()),
              'passed': True, 'worldsIncluded': False, 'jarsIncluded': False}
    (REVIEW / 'server-patch-package.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ['file', 'bytes', 'sha256', 'passed']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
