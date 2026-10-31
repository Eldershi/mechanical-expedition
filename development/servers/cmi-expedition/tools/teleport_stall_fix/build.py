"""Build the additive server-only cold-chunk/teleport compatibility patch."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[4]
TOOLS = Path(__file__).resolve().parent
PERF = ROOT / 'clients/cmi-expedition/tools/teleport_stall_fix/railway_perf'
BUILD = ROOT / 'servers/cmi-expedition/evidence/teleport-fix-20261020/build'
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')

def main():
    BUILD.mkdir(parents=True, exist_ok=True)
    classes = BUILD / 'classes'
    if classes.exists():
        shutil.rmtree(classes)
    classes.mkdir()
    dependencies = [
        LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
        LIBS / 'net/minecraftforge/forge/1.20.1-47.4.10/forge-1.20.1-47.4.10-universal.jar',
        next((ROOT / 'clients/cmi-expedition/instance/mods').glob('tongdarailway_for_forge-*.jar')),
    ]
    for package in ['org/spongepowered/mixin', 'com/mojang/brigadier', 'com/mojang/datafixerupper',
                    'it/unimi/dsi/fastutil', 'org/slf4j/slf4j-api', 'com/google/guava',
                    'com/google/code/gson', 'org/jetbrains/annotations']:
        dependencies.extend((LIBS / package).rglob('*.jar'))
    sources = []
    for directory in [TOOLS / 'async_teleport/src', TOOLS / 'offthread_chunk_future/src', PERF / 'src']:
        sources.extend(sorted(directory.rglob('*.java')))
    result = subprocess.run(['javac', '--release', '17', '-proc:none', '-encoding', 'UTF-8',
        '-cp', ':'.join(map(str, dependencies)), '-d', str(classes), *map(str, sources)],
        text=True, capture_output=True)
    (BUILD / 'compile.log').write_text(result.stdout + result.stderr)
    if result.returncode:
        raise SystemExit(result.stderr)
    configs = {
        'expedition-async-teleport.mixins.json': {
            'required': True, 'minVersion': '0.8', 'package': 'expedition.teleport.mixin',
            'compatibilityLevel': 'JAVA_17', 'mixins': ['TeleportCommandMixin'],
            'injectors': {'defaultRequire': 1}},
        'expedition-chunkfuture.mixins.json': {
            'required': True, 'minVersion': '0.8', 'package': 'expedition.chunkfuture.mixin',
            'compatibilityLevel': 'JAVA_17', 'mixins': ['OffThreadStructureChunkMixin'],
            'injectors': {'defaultRequire': 1}},
        'expedition-railway-perf.mixins.json': json.loads((PERF / 'expedition-railway-perf.mixins.json').read_text()),
    }
    jar = BUILD / 'expedition-teleport-fix-1.0.0.jar'
    with zipfile.ZipFile(jar, 'w', zipfile.ZIP_DEFLATED) as z:
        manifest = 'Manifest-Version: 1.0\nMixinConfigs: ' + ','.join(configs) + '\n\n'
        # Manifest physical lines must be <=72 bytes (continuation starts with a space).
        wrapped = []
        for line in manifest.splitlines():
            while len(line.encode()) > 70:
                wrapped.append(line[:70]); line = ' ' + line[70:]
            wrapped.append(line)
        z.writestr('META-INF/MANIFEST.MF', '\r\n'.join(wrapped) + '\r\n')
        z.writestr('META-INF/mods.toml', '''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_teleport_fix"
version="1.0.0"
displayName="Expedition Async Destination Preparation"
displayTest="IGNORE_SERVER_VERSION"
[[dependencies.expedition_teleport_fix]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
[[dependencies.expedition_teleport_fix]]
modId="tongdarailway_for_forge"
mandatory=true
versionRange="[0.0.4.3.3-SNAPSHOT]"
''')
        z.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 15,
            'description': 'Async cold destination preparation and exact railway sampling budget'}}))
        for name, config in configs.items():
            z.writestr(name, json.dumps(config))
        for file in sorted(classes.rglob('*.class')):
            z.write(file, file.relative_to(classes).as_posix())
    value = {'jar': str(jar), 'sha256': hashlib.sha256(jar.read_bytes()).hexdigest(),
             'classes': len(list(classes.rglob('*.class'))), 'sourceFiles': list(map(str, sources)),
             'sourceHashes': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
             'mixinConfigs': configs, 'productionInstalled': False}
    (BUILD / 'build.json').write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: value[k] for k in ['jar', 'sha256', 'classes']}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
