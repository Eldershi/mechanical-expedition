from pathlib import Path
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[4]
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
SERVER = WORKSPACE / 'servers/cmi-expedition/instance'
BUILD = ROOT / 'build'
BUILD.mkdir(exist_ok=True)
CLASSES = BUILD / 'classes'
if CLASSES.exists():
    shutil.rmtree(CLASSES)
CLASSES.mkdir(exist_ok=True)
TONGDA = next((SERVER / 'mods').glob('tongdarailway_for_forge-*.jar'))
dependencies = [
    LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
    TONGDA,
    SERVER / 'libraries/org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar',
]
for dependency in ('com/mojang/datafixerupper', 'com/google/guava', 'org/slf4j/slf4j-api',
                   'net/minecraftforge/fmlcore', 'net/minecraftforge/javafmllanguage'):
    dependencies.extend((SERVER / 'libraries' / dependency).rglob('*.jar'))
cp = ':'.join(map(str, dependencies))
result = subprocess.run([
    'javac', '--release', '17', '-proc:none', '-encoding', 'UTF-8', '-cp', cp,
    '-d', str(CLASSES), *map(str, (ROOT/'src').rglob('*.java')), str(ROOT/'test/ExactSamplerHarness.java')
], capture_output=True, text=True)
(BUILD/'compile.log').write_text(result.stdout+result.stderr)
assert result.returncode == 0, result.stderr
result = subprocess.run(['java', '-cp', f'{CLASSES}:{TONGDA}', 'ExactSamplerHarness'],
                        capture_output=True, text=True, timeout=45)
(BUILD/'determinism-test.log').write_text(result.stdout+result.stderr)
assert result.returncode == 0, result.stdout+result.stderr
(BUILD/'dependencies.json').write_text(json.dumps(list(map(str, dependencies)), ensure_ascii=False, indent=2))
print(result.stdout)
print('Compiled all mixin/helper classes; this is a standalone sampler test, not a Mixin runtime or game test.')
