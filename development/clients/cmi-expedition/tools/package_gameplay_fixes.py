"""Package the common 2026-10-19 fixes without worlds or server connection settings."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
OUT = PROJECT / 'releases/0.2.0-test.3'
EVIDENCE = ROOT / 'evidence/gameplay-fixes-20261019'
PAYLOAD = (
    'config/curios-common.toml',
    'config/creeper_firework-common.toml',
    'config/ftbquests/quests/chapters/steam_railway.snbt',
    'kubejs/startup_scripts/expedition/AlwaysEat.js',
    'kubejs/startup_scripts/expedition/NoPlayerDamage.js',
    'kubejs/startup_scripts/expedition/NetherBreathing.js',
    'mods/civillis-forge-2.0.1-release+mc1.20.1.jar',
    'mods/expedition-creeper-firework-compat-1.0.0.jar',
    'mods/expedition-railway-avoidance-1.0.0.jar',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def without_descriptions(value):
    if isinstance(value, dict):
        return {k: without_descriptions(v) for k, v in value.items() if k != 'description'}
    if isinstance(value, list):
        return [without_descriptions(v) for v in value]
    return value


def main():
    # Publish only after the combined Forge probe has actually passed.
    probe = ROOT / 'evidence/gameplay-batch-20261019/test-server/kubejs/exported/gameplay-batch-regression.json'
    result = json.loads(probe.read_text())
    assert result['passed'], 'Combined runtime regression must pass before packaging'
    test_server = ROOT / 'evidence/gameplay-batch-20261019/test-server'
    data = {}
    for name in PAYLOAD:
        blob = (ROOT / 'overlay' / name).read_bytes()
        client = (ROOT / 'instance' / name).read_bytes()
        server = (PROJECT / 'servers/cmi-expedition/instance' / name).read_bytes()
        if name == 'config/curios-common.toml':
            import tomllib
            assert tomllib.loads(blob.decode()) == tomllib.loads(client.decode()) == tomllib.loads(server.decode())
        else:
            assert blob == client == server, name
        tested = (test_server / name).read_bytes()
        if name == 'config/ftbquests/quests/chapters/steam_railway.snbt':
            # FTB/QuestEnhance rewrites this file's layout at startup. The source
            # change is three description strings only; validate gameplay data
            # against its before-change backup instead of its rewritten layout.
            from ftb_snbt import loads
            before = EVIDENCE / 'nether-fireworks/before/clients/cmi-expedition/instance' / name
            assert without_descriptions(loads(before.read_text())) == without_descriptions(loads(blob.decode()))
        elif name.endswith('.toml'):
            import tomllib
            assert tomllib.loads(tested.decode()) == tomllib.loads(blob.decode()), ('Tested config differs', name)
        else:
            assert tested == blob, ('Tested payload differs', name)
        data[name] = blob
    notes = (EVIDENCE / '更新说明.txt').read_bytes()
    manifest = [{'path': name, 'bytes': len(blob), 'sha256': digest(blob)} for name, blob in data.items()]
    OUT.mkdir(parents=True, exist_ok=True)
    package = OUT / '机械动力-远征-0.2.0-test.3-玩法修复共用补丁.zip'
    temporary = package.with_suffix('.building')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, blob in data.items():
            z.writestr(name, blob)
        z.writestr('玩法修复说明.txt', b'\xef\xbb\xbf' + notes)
        z.writestr('gameplay-fix-files.json', encoded(manifest))
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        assert set(z.namelist()) == set(PAYLOAD) | {'玩法修复说明.txt', 'gameplay-fix-files.json'}
        for row in manifest:
            assert digest(z.read(row['path'])) == row['sha256']
    temporary.replace(package)
    (OUT / '玩法修复说明.txt').write_bytes(b'\xef\xbb\xbf' + notes)
    report = {
        'at': datetime.now().astimezone().isoformat(), 'file': str(package),
        'sha256': digest(package.read_bytes()), 'bytes': package.stat().st_size,
        'files': manifest, 'archiveIntegrityPassed': True,
        'runtimeEvidence': str(probe), 'remoteDeploymentComplete': False,
        'worldsIncluded': False, 'serverPropertiesIncluded': False,
    }
    (EVIDENCE / 'patch-package.json').write_bytes(encoded(report))
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
