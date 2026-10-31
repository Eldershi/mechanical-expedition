"""Assemble reviewed sources; never reads player worlds/accounts into the ZIP."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
ACTIVE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
OUT = ROOT / 'package'
NAME = 'Expedition-Combined-Patch-20261029.zip'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def build():
    OUT.mkdir(exist_ok=True)
    payload = OUT / 'client-payload'
    payload.mkdir(exist_ok=True)
    operations, protected, sources = [], None, []
    for name in ('upstream-sync-20261029', 'equipment-mods-20261029'):
        release = PROJECT / 'releases' / name
        manifest = json.loads((release / 'client-manifest.json').read_text())
        assert manifest['validationStatus'] == 'validated'
        if protected is None:
            protected = manifest['protectedCatalogs']
        assert protected == manifest['protectedCatalogs']
        sources.append({'release': name, 'manifestSha256': sha(release / 'client-manifest.json'),
                        'operations': len(manifest['operations'])})
        for row in manifest['operations']:
            assert row['path'] not in {op['path'] for op in operations}
            operations.append(dict(row))
            if row['action'] == 'write':
                source = release / 'client-payload' / row['path']
                assert sha(source) == row['afterSha256']
                target = payload / row['path']
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
    accepted = {
        'mods/expedition-upstream-compat-1.0.0.jar': ['07800466d0f737e33fa49bb229ecad2c7673e491b509fe294f6d393277e421e2'],
        'kubejs/server_scripts/expedition/UpstreamSyncAudit.js': [
            '969e389f613df3dd234bef621ec5c01b9eaceee8c65ebc21990712b116e6251d',
            '9079cb3deec6c9d898d9fa41acb5a703403dbe3b88d837ef129af4f0bf1e1472',
            '9bcd44fee3444bd5c5547504be20027e7f8025b2e7147365e4897dd61a3748ee']}
    for row in operations:
        if row['path'] in accepted:
            row['acceptedBeforeSha256'] = accepted[row['path']]
    hnn = PROJECT / 'design/hostile-networks-create-v18-resource-only-20261029'
    hnn_manifest = json.loads((hnn / 'evidence/release-manifest.json').read_text())
    pack = hnn / 'dist/Expedition-HNN-v18-Resource-Only-1.20.1.zip'
    assert hnn_manifest['pure_resource_pack'] and sha(pack) == hnn_manifest['sha256']
    rel = 'config/paxi/resourcepacks/' + pack.name
    (payload / rel).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pack, payload / rel)
    operations.append({'path': rel, 'action': 'write', 'beforeSha256': None,
                       'afterSha256': sha(pack), 'bytes': pack.stat().st_size})
    retired = {}
    for directory in sorted((PROJECT / 'design').glob('hostile-networks-create*-20261029')):
        for source in list((directory / 'dist').glob('Expedition-HNN-*.zip')) + list((directory / 'client/dist').glob('expedition-hnn-gui-*.jar')):
            if source.name == pack.name or 'Review' in source.name:
                continue
            folders = ('mods',) if source.suffix == '.jar' else ('resourcepacks', 'config/paxi/resourcepacks')
            for folder in folders:
                hashes = retired.setdefault(folder + '/' + source.name, [])
                if sha(source) not in hashes:
                    hashes.append(sha(source))
    required = {}
    for name in ('create-1.20.1-6.0.8.jar', 'kubejs-forge-2001.6.5-build.26.jar',
                 'HostileNeuralNetworks-1.20.1-5.3.3.jar', 'Placebo-1.20.1-8.6.3.jar',
                 'Paxi-1.20-Forge-4.0.jar', 'geckolib-forge-1.20.1-4.8.4.jar',
                 'curios-forge-5.14.1+1.20.1.jar', 'BCLib-20.0.13.jar'):
        required['mods/' + name] = sha(ACTIVE / 'mods' / name)
    prior = PROJECT / 'releases/session-patch-20261028'
    prior_manifest = json.loads((prior / 'manifest.json').read_text())
    for name in ['manifest.json', *prior_manifest['packageFiles']]:
        target = OUT / 'prerequisite' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(prior / name, target)
    manifest = {'schemaVersion': 1, 'patchId': 'expedition-combined-20261029',
                'minecraft': '1.20.1', 'loader': 'Forge', 'validationStatus': 'validated',
                'supportedBase': 'Expedition Full Client 20261027 plus known session updates; not stock CMI',
                'protectedCatalogs': protected, 'requiredFiles': required,
                'retiredFiles': retired, 'sources': sources,
                'prerequisiteManifestSha256': sha(prior / 'manifest.json'),
                'hnnResourcePackSha256': sha(pack), 'operations': operations,
                'summary': {'writes': sum(x['action'] == 'write' for x in operations),
                            'deletes': sum(x['action'] == 'delete' for x in operations),
                            'payloadBytes': sum(x['bytes'] for x in operations)}}
    (OUT / 'client-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    for name in ('install_client.py', 'bundle_support.py', 'README.txt', 'CHANGELOG.txt'):
        shutil.copy2(ROOT / name, OUT / name)
    evidence = OUT / 'verification'
    evidence.mkdir(exist_ok=True)
    (evidence / 'source-summary.json').write_text(json.dumps({
        'upstreamCommit': '77f6e7adafa60007b34f464e8e810bd699649bdd',
        'machineSelection': {'passed': True, 'routes': 3},
        'equipment': ['Scorched Guns 2 0.5.5', 'Protection Pixel 2.2.1', 'Framework 0.8.0'],
        'multiplayerTest': {'realClients': 2, 'roundTrips': 9, 'issue49Reproduced': False,
                            'observerMaxFrameMs': 190.124, 'framesOver1s': 0,
                            'scope': 'Current production async teleport; shaders off; no uninstalled-mod A/B'},
        'hnn': {'pureResources': True, 'files': 27, 'sha256': sha(pack),
                'worldGuiAcceptance': False, 'startupValidation': True},
        'protectedCatalogs': protected,
        'excluded': ['worlds', 'accounts', 'launcher settings', 'test-client options',
                     'server backups', 'teleport performance experiments', 'superseded HNN Java components']
    }, ensure_ascii=False, indent=2) + '\n')
    if (ROOT / 'verification/bundle-validation.json').exists():
        shutil.copy2(ROOT / 'verification/bundle-validation.json', evidence / 'bundle-validation.json')
    files = {p.relative_to(OUT).as_posix(): sha(p) for p in sorted(OUT.rglob('*'))
             if p.is_file() and p.name != 'package-integrity.json' and '__pycache__' not in p.parts}
    (OUT / 'package-integrity.json').write_text(json.dumps({'algorithm': 'sha256', 'files': files}, ensure_ascii=False, indent=2) + '\n')
    archive = ROOT / NAME
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                z.write(p, 'Expedition-Combined-Patch-20261029/' + p.relative_to(OUT).as_posix())
    result = {'archive': archive.name, 'sha256': sha(archive), 'bytes': archive.stat().st_size,
              **manifest['summary'], 'hnnRetirementPaths': len(retired)}
    (ROOT / (NAME + '.sha256')).write_text(result['sha256'] + '  ' + NAME + '\n')
    (ROOT / 'build-result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    build()
