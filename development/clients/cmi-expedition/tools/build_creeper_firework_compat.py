"""Build the scoped harmless-firework adapter; installation is a separate step."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

CLIENT = Path(__file__).resolve().parents[1]
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
EVIDENCE = CLIENT / 'evidence/gameplay-fixes-20261019/nether-fireworks'
CLASSES = EVIDENCE / 'classes'
JAR = CLIENT / 'downloads/expedition-creeper-firework-compat-1.0.0.jar'


def build():
    if CLASSES.exists():
        shutil.rmtree(CLASSES)
    CLASSES.mkdir(parents=True, exist_ok=True)
    libraries = [
        LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
        CLIENT / 'instance/mods/creeper_firework-2.1.0.b.jar',
    ]
    for namespace in ['org/spongepowered/mixin', 'com/mojang/brigadier', 'com/google/guava',
                      'com/mojang/datafixerupper', 'net/minecraftforge/forge']:
        libraries.extend((LIBS / namespace).rglob('*.jar'))
    sources = sorted((CLIENT / 'tools/compat/fireworks').glob('*.java'))
    result = subprocess.run([
        'javac', '--release', '17', '-proc:none', '-encoding', 'UTF-8',
        '-cp', ':'.join(map(str, libraries)), '-d', str(CLASSES), *map(str, sources),
    ], capture_output=True, text=True)
    (EVIDENCE / 'compile.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    metadata = '''modLoader="lowcodefml"
loaderVersion="[47,)"
license="MIT"
[[mods]]
modId="expedition_creeper_firework_compat"
version="1.0.0"
displayName="Expedition Creeper Firework compatibility"
description="Harmless fireworks for selected creeper variants; Nucleeper and Solar boss behavior stays native."
'''
    for mod, version in [('minecraft', '[1.20.1,1.20.2)'), ('creeper_firework', '[2.1.0.b]'),
                         ('creeperoverhaul', '[3.0.2]'), ('ad_astra', '[1.15.21]'),
                         ('alexscaves', '[2.0.2]'), ('illageandspillage', '[1.2.8]'),
                         ('legendary_monsters', '[1.20.1]')]:
        metadata += f'''
[[dependencies.expedition_creeper_firework_compat]]
modId="{mod}"
mandatory=true
versionRange="{version}"
ordering="AFTER"
side="BOTH"
'''
    with zipfile.ZipFile(JAR, 'w', zipfile.ZIP_DEFLATED) as archive:
        entries = {
            'META-INF/MANIFEST.MF': b'Manifest-Version: 1.0\nMixinConfigs: expedition-creeper-firework.mixins.json\n\n',
            'META-INF/mods.toml': metadata.encode(),
            'pack.mcmeta': json.dumps({'pack': {'pack_format': 15, 'description': 'Expedition Creeper Firework compatibility'}}).encode(),
            'expedition-creeper-firework.mixins.json': json.dumps({
                'required': True, 'minVersion': '0.8', 'package': 'expedition.fireworks.mixin',
                'compatibilityLevel': 'JAVA_17', 'mixins': ['OverhaulFireworkMixin', 'SulfurFireworkMixin',
                    'GumbeeperFireworkMixin', 'KaboomerFireworkMixin', 'BomberFireworkMixin'],
                'injectors': {'defaultRequire': 1},
            }).encode(),
        }
        entries.update({p.relative_to(CLASSES).as_posix(): p.read_bytes() for p in CLASSES.rglob('*.class')})
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    report = {'jar': str(JAR.relative_to(CLIENT)), 'sha256': hashlib.sha256(JAR.read_bytes()).hexdigest(),
              'bytes': JAR.stat().st_size, 'classes': len(list(CLASSES.rglob('*.class'))),
              'upstreamJarsModified': False, 'status': 'built_requires_runtime_validation'}
    (EVIDENCE / 'build.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
