"""Isolated, offline Ponder integration check; never reads launcher accounts."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / 'instance'
EVIDENCE = ROOT / 'evidence/ponder-addons'
TEST = EVIDENCE / 'test-instance'
STAGE = ROOT / 'downloads/ponder-addons'
WORLD = 'Ponder-Compatibility-Test'


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare():
    assert not TEST.exists(), 'Test instance already exists; preserve its evidence.'
    TEST.mkdir(parents=True)
    for name in ['config', 'defaultconfigs', 'kubejs', 'resourcepacks', 'ldlib',
                 'fancymenu_data', 'patchouli_books', 'moonlight-global-datapacks',
                 'datapacks', 'hotai', 'tlm_custom_pack', 'ESM']:
        source = LIVE / name
        if source.exists():
            shutil.copytree(source, TEST / name)
    for name in ['options.txt', 'patchouli_data.json', 'rhino.local.properties']:
        if (LIVE / name).exists():
            shutil.copy2(LIVE / name, TEST / name)
    shutil.rmtree(TEST / 'kubejs/exported', ignore_errors=True)
    (TEST / 'kubejs/exported').mkdir()
    (TEST / 'mods').mkdir()
    inventory = {}
    for source in sorted((LIVE / 'mods').glob('*.jar')):
        inventory[source.name] = sha(source)
        (TEST / 'mods' / source.name).symlink_to(source)
    for source in sorted(STAGE.glob('*.jar')):
        if source.name.startswith('expedition-ponder-ui-'):
            continue
        if (TEST / 'mods' / source.name).exists():
            assert sha(TEST / 'mods' / source.name) == sha(source)
            continue
        (TEST / 'mods' / source.name).symlink_to(source)
    shutil.copytree(LIVE / 'saves/新的世界', TEST / 'saves' / WORLD,
                    ignore=shutil.ignore_patterns('session.lock'))
    (TEST / 'screenshots').mkdir()
    dump(EVIDENCE / 'before.json', {
        'at': datetime.now().astimezone().isoformat(), 'liveInstance': str(LIVE),
        'testInstance': str(TEST), 'modHashes': inventory,
        'sourceHash': sha(LIVE / 'SOURCE.json'),
        'optionsHash': sha(LIVE / 'options.txt'),
        'worldHashes': {str(p.relative_to(LIVE / 'saves')): sha(p)
                        for p in (LIVE / 'saves').rglob('*') if p.is_file()},
    })
    print('Prepared isolated test instance:', TEST)


def launch():
    launcher = (Path.home() / 'Library/Application Support/Swift Craft Launcher')
    with sqlite3.connect(f'file:{launcher}/data/data.db?mode=ro', uri=True) as conn:
        row = conn.execute('SELECT data_json FROM game_versions WHERE game_name = ?',
                           ('机械远征-CMI-迁移测试',)).fetchone()
    data = json.loads(row[0])
    assert data['gameVersion'] == '1.20.1' and data['modVersion'] == '47.4.10'
    replacements = {
        'xms': '512', 'xmx': '8192', 'game_directory': str(TEST),
        'auth_player_name': 'MigrationTest', 'auth_access_token': '0',
        'auth_uuid': uuid.uuid3(uuid.NAMESPACE_DNS, 'OfflinePlayer:MigrationTest').hex,
        'auth_xuid': '0',
    }
    args = [re.sub(r'\$\{([^}]+)\}', lambda m: replacements[m[1]], arg)
            for arg in data['launchCommand']]
    args[args.index('--userType') + 1] = 'legacy'
    args.extend(['--quickPlaySingleplayer', WORLD])
    java = ROOT / 'runtime/temurin17/jdk-17.0.20.1+1-jre/Contents/Home/bin/java'
    assert java.is_file()
    environment = dict(os.environ)
    environment.pop('__CFBundleIdentifier', None)
    receipt = {'startedAt': datetime.now().astimezone().isoformat(),
               'minecraft': '1.20.1', 'forge': '47.4.10', 'java': str(java),
               'maxHeapMiB': 8192, 'instance': str(TEST), 'world': WORLD,
               'mode': 'offline disposable copy; no account credentials'}
    dump(EVIDENCE / 'launch.json', receipt)
    with (EVIDENCE / 'console.log').open('w') as output:
        process = subprocess.Popen([str(java), *args], cwd=TEST, env=environment,
                                   stdout=output, stderr=subprocess.STDOUT)
        dump(EVIDENCE / 'pid.json', {'pid': process.pid})
        print('Started isolated test PID', process.pid, flush=True)
        code = process.wait()
    dump(EVIDENCE / 'exit.json', {'code': code,
                                'at': datetime.now().astimezone().isoformat()})
    print('Client exit:', code)


def build():
    libs = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
    inspect = EVIDENCE / 'inspect-libs'
    inspect.mkdir(exist_ok=True)
    with zipfile.ZipFile(STAGE / 'mekanism_ponders-1.0.4-1.20.1.jar') as archive:
        for name in archive.namelist():
            if name.startswith('META-INF/jarjar/') and name.endswith('.jar'):
                (inspect / Path(name).name).write_bytes(archive.read(name))
    classpath = [libs / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
                 *sorted(inspect.glob('*.jar')), *sorted((LIVE / 'mods').glob('*.jar')),
                 *sorted(STAGE.glob('*.jar'))]
    for name in ['com/google/code/gson', 'com/google/guava', 'com/mojang', 'org/slf4j',
                 'org/apache', 'org/lwjgl', 'org/joml', 'io/netty', 'it/unimi/dsi', 'net/minecraftforge']:
        classpath.extend(sorted((libs / name).rglob('*.jar')))
    classes = EVIDENCE / 'probe-classes'
    classes.mkdir(exist_ok=True)
    result = subprocess.run(['javac', '--release', '17', '-encoding', 'UTF-8', '-cp',
        ':'.join(map(str, classpath)), '-d', str(classes),
        str(ROOT / 'tools/diagnostics/PonderProbe.java')], capture_output=True, text=True)
    (EVIDENCE / 'probe-compile.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    with zipfile.ZipFile(TEST / 'mods/expedition-ponder-probe-1.0.jar', 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('META-INF/mods.toml',
            'modLoader="lowcodefml"\nloaderVersion="[47,)"\nlicense="Private disposable diagnostic"\n'
            '[[mods]]\nmodId="expedition_ponder_probe"\nversion="1.0"\n'
            'displayName="Disposable Ponder integration probe"\n')
        archive.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 15,
            'description': 'Disposable Ponder integration probe'}}))
        for source in classes.rglob('*.class'):
            archive.write(source, str(source.relative_to(classes)))
    (TEST / 'kubejs/client_scripts/event/PonderCompatibilityProbe.js').write_text(
        "// Disposable copy only.\n"
        "const ExpeditionPonderProbe = Java.loadClass('expedition.ponder.PonderProbe')\n"
        "ClientEvents.tick(event => ExpeditionPonderProbe.tick())\n")
    print('Built disposable probe in isolated instance only')


def install():
    validation = json.loads((EVIDENCE / 'validation.json').read_text())
    assert validation.get('passed'), 'Clean runtime validation must pass before installation.'
    result = json.loads((TEST / 'kubejs/exported/ponder-compat-result.json').read_text())
    assert result.get('passed'), 'Runtime test must pass before installation.'
    before = json.loads((EVIDENCE / 'before.json').read_text())
    backup = ROOT / ('backups/before-ponder-addons-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    backup.mkdir(parents=True)
    shutil.copy2(LIVE / 'SOURCE.json', backup / 'SOURCE.json')
    dump(backup / 'mods-before.json', before['modHashes'])
    rows = json.loads((EVIDENCE / 'download-receipt.json').read_text())
    sources = json.loads((LIVE / 'SOURCE.json').read_text())
    for row in rows:
        source = STAGE / row['file']
        assert sha(source) == row['sha256']
        target = LIVE / 'mods' / source.name
        assert not target.exists(), 'Refuse to overwrite an existing mod.'
        shutil.copy2(source, target)
        sources['sources']['mods/' + source.name] = {
            'url': row['download'], 'origin': 'approved_ponder_addon',
            'projectUrl': row['source'], 'sha256': row['sha256'],
        }
    configs = []
    for name in ['iss_ponder-client.toml', 'quark_ponders-client.toml']:
        source = TEST / 'config' / name
        target = LIVE / 'config' / name
        if source.exists() and not target.exists():
            shutil.copy2(source, target)
            configs.append({'file': name, 'sha256': sha(target)})
    dump(LIVE / 'SOURCE.json', sources)
    preserved = all((LIVE / 'mods' / name).is_file() and sha(LIVE / 'mods' / name) == digest
                    for name, digest in before['modHashes'].items())
    worlds = {str(p.relative_to(LIVE / 'saves')): sha(p)
              for p in (LIVE / 'saves').rglob('*') if p.is_file()}
    dump(EVIDENCE / 'installation.json', {
        'at': datetime.now().astimezone().isoformat(), 'backup': str(backup),
        'installed': rows, 'newDefaultConfigs': configs, 'existingModsUnchanged': preserved,
        'optionsUnchanged': sha(LIVE / 'options.txt') == before['optionsHash'],
        'worldsUnchanged': worlds == before['worldHashes'],
        'testResult': str(TEST / 'kubejs/exported/ponder-compat-result.json'),
    })
    assert preserved and worlds == before['worldHashes']
    print('Installed three tested addons; backup:', backup)


def validate():
    result = json.loads((TEST / 'kubejs/exported/ponder-compat-result.json').read_text())
    inventory = json.loads((TEST / 'kubejs/exported/ponder-compat-inventory.json').read_text())
    console = (EVIDENCE / 'console.log').read_text(errors='replace')
    scripts = {}
    for name in ['startup', 'client', 'server']:
        lines = (TEST / 'logs/kubejs' / (name + '.log')).read_text(errors='replace').splitlines()
        baseline_path = LIVE / 'logs/kubejs' / (name + '.log')
        baseline_lines = baseline_path.read_text(errors='replace').splitlines()
        def error_headers(source):
            headers = set()
            for line in source:
                if '[ERROR]' not in line:
                    continue
                text = re.sub(r'^!\s*', '', line.split('[ERROR]', 1)[1].strip())
                if not text.startswith(('at ', '...')):
                    headers.add(text)
            return headers
        baseline_errors, observed_errors = error_headers(baseline_lines), error_headers(lines)
        scripts[name] = {'summaries': [line for line in lines if re.search(r'Loaded \d+/\d+ KubeJS', line)],
                         'errorLineCount': sum('[ERROR]' in line for line in lines),
                         'baselineErrorHeaders': sorted(baseline_errors),
                         'observedErrorHeaders': sorted(observed_errors),
                         'newErrors': sorted(observed_errors - baseline_errors),
                         'baselineLog': str(baseline_path)}
    checks = {
        'allIntegrationCasesPassed': result['passed'],
        'allThreeAddonsLoaded': all(id in inventory['loadedVersions'] for id in
                                   ['iss_ponder', 'mekanism_ponders', 'quark_ponders']),
        'scriptsLoadedWithoutCompileErrors': all(row['summaries'] and
            all('with 0 errors' in line for line in row['summaries']) for row in scripts.values()),
        'noNewScriptRuntimeErrors': all(not row['newErrors'] for row in scripts.values()),
        'playerJoined': 'logged in with entity id' in console,
        'previewSessionsCleanedUp': result['sessionsAfterClose'] == 0,
        'noCrashReports': not list((TEST / 'crash-reports').glob('*.txt')),
        'testWorldSaved': 'ThreadedAnvilChunkStorage: All dimensions are saved' in console,
    }
    known = [line for line in console.splitlines() if
             'mekanism_ponders.mixins.json does not specify "minVersion"' in line]
    summary = {
        'checkedAt': datetime.now().astimezone().isoformat(), 'passed': all(checks.values()),
        'checks': checks, 'scripts': scripts, 'loadedVersions': inventory['loadedVersions'],
        'uniqueAddedScenes': inventory['uniqueAddedScenes'],
        'sceneCountByNamespace': {ns: sum(row['kind'] == 'scene' and row.get('namespace') == ns
            for row in result['results']) for ns in ['mekanism_ponders', 'quark_ponders']},
        'caseCount': len(result['results']), 'knownNonfatalAddonMessages': known,
        'spellCases': [row for row in result['results'] if row['kind'] == 'spell'],
        'screenshots': [str(path.relative_to(EVIDENCE)) for path in sorted((TEST / 'screenshots').glob('*.png'))],
        'limitations': ['Local client and integrated server; no dedicated-server or remote-multiplayer test.',
                       'Six representative spell previews; not an exhaustive test of every spell or addon.'],
    }
    dump(EVIDENCE / 'validation.json', summary)
    print(json.dumps({'passed': summary['passed'], 'checks': checks,
                      'loadedVersions': inventory['loadedVersions'], 'cases': len(result['results'])},
                     ensure_ascii=False, indent=2))
    assert summary['passed'], 'Resolve failed checks before installing.'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'build', 'launch', 'validate', 'install'])
    actions = {'prepare': prepare, 'build': build, 'launch': launch, 'validate': validate, 'install': install}
    actions[parser.parse_args().action]()
