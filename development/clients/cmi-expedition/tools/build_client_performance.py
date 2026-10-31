"""Build, but do not install, recipe counting, DH queue backoff and resolution-floor compatibility."""
from pathlib import Path
import json
import argparse
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
parser=argparse.ArgumentParser()
parser.add_argument('--output-dir',type=Path,default=ROOT/'evidence/performance-community-20261017')
OUT=parser.parse_args().output_dir.resolve()
OUT.mkdir(parents=True,exist_ok=True)
classes = OUT / 'client-performance-classes'
if classes.exists():
    shutil.rmtree(classes)
classes.mkdir(parents=True)
libraries = [LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar']
libraries.extend((LIBS / 'org/spongepowered/mixin').rglob('*.jar'))
libraries.append(ROOT/'instance/mods/DistantHorizons-3.3.3-1.20.1-fabric-forge.jar')
libraries.extend((ROOT/'instance/mods').glob('FarmersDelight-*.jar'))
for name in ['com/google/guava', 'com/mojang/brigadier', 'com/mojang/datafixerupper']:
    libraries.extend((LIBS/name).rglob('*.jar'))
libraries.extend((LIBS/'org/lwjgl/lwjgl-glfw').rglob('lwjgl-glfw-3.3.1.jar'))
sources = sorted((ROOT / 'tools/compat/performance').glob('*.java'))
result = subprocess.run(['javac', '--release', '17', '-proc:none', '-encoding', 'UTF-8',
                         '-cp', ':'.join(map(str, libraries)), '-d', str(classes), *map(str, sources)],
                        capture_output=True, text=True)
(OUT / 'client-performance-compile.log').write_text(result.stdout + result.stderr)
if result.returncode:
    raise RuntimeError(result.stderr)
jar = OUT / 'expedition-client-performance-1.0.0.jar'
with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\nMixinConfigs: expedition-client-performance.mixins.json\n\n')
    z.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 15, 'description': 'Expedition client performance compatibility'}}))
    z.writestr('expedition-client-performance.mixins.json', json.dumps({
        'required': True, 'minVersion': '0.8', 'package': 'expedition.performance.client',
        'compatibilityLevel': 'JAVA_17', 'client': ['RecipeManagerAccess', 'JectRecipeCount', 'DhQueueBackoff', 'NativeWindowSize', 'RenderResolutionFloor'],
        'injectors': {'defaultRequire': 1}}))
    z.writestr('META-INF/mods.toml', '''modLoader="lowcodefml"
loaderVersion="[47,)"
license="MIT"
clientSideOnly=true
[[mods]]
modId="expedition_client_performance"
version="1.0.0"
displayName="Expedition Client Performance"
displayTest="IGNORE_ALL_VERSION"
description="Reduce repeated recipe/queue allocation and preserve the authorized 1920x1080 render floor."
[[dependencies.expedition_client_performance]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
[[dependencies.expedition_client_performance]]
modId="just_enough_crafting_tree"
mandatory=false
versionRange="[2.4.0-alpha.6]"
side="CLIENT"
''')
    for file in sorted(classes.rglob('*.class')):
        z.write(file, file.relative_to(classes).as_posix())
print(json.dumps({'built': str(jar), 'installed': False, 'bytes': jar.stat().st_size}))
