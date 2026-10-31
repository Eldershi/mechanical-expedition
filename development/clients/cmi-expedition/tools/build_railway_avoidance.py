"""Build the 1.20.1/Tongda 0.0.4.3.3 candidate-avoidance compatibility mod."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
SERVER_LIBS = ROOT.parents[1] / 'servers/cmi-expedition/instance/libraries'
EVIDENCE = ROOT / 'evidence/client-gameplay-20261019/railway'
CLASSES = EVIDENCE / 'classes'
JAR = ROOT / 'downloads/optimization/expedition-railway-avoidance-1.0.0.jar'


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    if CLASSES.exists():
        shutil.rmtree(CLASSES)
    CLASSES.mkdir()
    libraries = [LIBS / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
                 next((ROOT / 'instance/mods').glob('tongdarailway_for_forge-*.jar'))]
    libraries += list((SERVER_LIBS / 'net/minecraftforge/forge/1.20.1-47.4.10').glob('*universal.jar'))
    for dependency in ('org/spongepowered/mixin', 'com/google/code/gson', 'com/google/guava',
                       'com/mojang/datafixerupper', 'org/slf4j/slf4j-api'):
        libraries += list((LIBS / dependency).rglob('*.jar'))
    result = subprocess.run(['javac', '--release', '17', '-proc:none', '-encoding', 'UTF-8',
                             '-cp', ':'.join(map(str, libraries)), '-d', str(CLASSES),
                             *map(str, (ROOT / 'tools/railway_avoidance').glob('*.java'))],
                            capture_output=True, text=True)
    (EVIDENCE / 'compile.log').write_text(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    JAR.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(JAR, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF', 'Manifest-Version: 1.0\nMixinConfigs: expedition-railway.mixins.json\n\n')
        z.writestr('pack.mcmeta', json.dumps({'pack': {'pack_format': 15, 'description': 'Expedition railway structure avoidance'}}))
        z.writestr('expedition-railway.mixins.json', json.dumps({
            'required': True, 'minVersion': '0.8', 'package': 'expedition.railway.mixin',
            'compatibilityLevel': 'JAVA_17', 'mixins': ['StructureCandidateMixin', 'StationSizeAccessor'],
            'injectors': {'defaultRequire': 1}}))
        z.writestr('META-INF/mods.toml', '''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_railway_avoidance"
version="1.0.0"
displayName="Expedition Railway Structure Avoidance"
[[dependencies.expedition_railway_avoidance]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
[[dependencies.expedition_railway_avoidance]]
modId="tongdarailway_for_forge"
mandatory=true
versionRange="[0.0.4.3.3-SNAPSHOT]"
''')
        for p in CLASSES.rglob('*.class'):
            z.write(p, str(p.relative_to(CLASSES)))
    print(json.dumps({'built': str(JAR), 'sha256': hashlib.sha256(JAR.read_bytes()).hexdigest(),
                      'installed': False, 'runtimeValidation': 'required'}))


if __name__ == '__main__':
    main()
