#!/usr/bin/env python3
"""Build and verify the FTB Teams client compatibility add-on."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', type=Path, required=True)
    parser.add_argument('--libraries', type=Path, required=True)
    parser.add_argument('--java-home', type=Path, required=True)
    args = parser.parse_args()
    build = ROOT / 'build'
    classes = build / 'classes'
    classes.mkdir(parents=True, exist_ok=True)
    libs = args.libraries
    ftb = args.instance / 'mods/ftb-teams-forge-2001.3.2.jar'
    assert hashlib.sha256(ftb.read_bytes()).hexdigest() == 'b1cb4d82ea9f137a87e12a7aaf3329619294b56f7d70337dfd557a76e10b6e07'
    deps = [ftb, args.instance / 'mods/ftb-library-forge-2001.2.13.jar',
            libs / 'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
            libs / 'org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar']
    for name in ('asm', 'asm-tree', 'asm-analysis', 'asm-util', 'asm-commons'):
        deps.append(libs / f'org/ow2/asm/{name}/9.8/{name}-9.8.jar')
    for rel in ('com/mojang/authlib/4.0.43', 'com/google/guava/guava/31.1-jre',
                'com/google/code/gson/gson/2.10', 'org/apache/logging/log4j/log4j-api',
                'com/mojang/brigadier/1.1.8', 'com/mojang/datafixerupper/6.0.8',
                'org/jetbrains/annotations', 'it/unimi/dsi/fastutil/8.5.9'):
        deps.extend(sorted((libs / rel).rglob('*.jar')))
    cp = os.pathsep.join(map(str, deps))

    def run(name, command):
        result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=90)
        (build / name).write_text(result.stdout + result.stderr)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        return result.stdout.strip()

    sources = sorted((ROOT / 'src').rglob('*.java'))
    run('compile.log', [args.java_home / 'bin/javac', '--release', '17', '-proc:none', '-cp', cp,
                        '-d', classes, *sources])
    config = {'required': True, 'minVersion': '0.8', 'package': 'expedition.ftbteamscompat.mixin',
              'compatibilityLevel': 'JAVA_17', 'client': ['ClientIdentityMixin', 'InvitationSortMixin'],
              'injectors': {'defaultRequire': 1}}
    jar = build / 'expedition-ftb-teams-client-compat-1.0.0.jar'
    entries = {
        'META-INF/MANIFEST.MF': b'Manifest-Version: 1.0\r\nMixinConfigs: expedition-ftb-teams-client-compat.mixins.json\r\n\r\n',
        'expedition-ftb-teams-client-compat.mixins.json': json.dumps(config).encode(),
        'pack.mcmeta': json.dumps({'pack': {'pack_format': 15,
            'description': 'FTB Teams client identity and invitation compatibility'}}).encode(),
        'META-INF/mods.toml': b'''modLoader="lowcodefml"
loaderVersion="[47,)"
license="MIT"
[[mods]]
modId="expedition_ftb_teams_client_compat"
version="1.0.0"
displayName="Expedition FTB Teams Client Compatibility"
displayTest="IGNORE_SERVER_VERSION"
description="Resolve FTB Teams self identity from the current server connection and sort party invitations safely. Client only."
[[dependencies.expedition_ftb_teams_client_compat]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
side="CLIENT"
[[dependencies.expedition_ftb_teams_client_compat]]
modId="ftbteams"
mandatory=true
versionRange="[2001.3.2]"
side="CLIENT"
''',
    }
    for path in sorted((classes / 'expedition').rglob('*.class')):
        entries[path.relative_to(classes).as_posix()] = path.read_bytes()
    with zipfile.ZipFile(jar, 'w') as archive:
        for name, data in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(jar) as archive:
        assert json.loads(archive.read('pack.mcmeta'))['pack']['pack_format'] == 15
        assert not any(name.startswith(('net/', 'Standalone', 'VerifyTeam')) for name in archive.namelist())
    run('test-compile.log', [args.java_home / 'bin/javac', '--release', '17', '-proc:none', '-cp',
         str(classes) + os.pathsep + cp, '-d', classes, *sorted((ROOT / 'tests').rglob('*.java'))])
    service = classes / 'META-INF/services/org.spongepowered.asm.service.IMixinService'
    service.parent.mkdir(parents=True, exist_ok=True)
    service.write_text('StandaloneMixinService\n')
    (classes / 'META-INF/services/org.spongepowered.asm.service.IGlobalPropertyService').write_text('StandaloneProperties\n')
    runtime = os.pathsep.join(map(str, [classes, jar, *deps]))
    verification = run('mixin-verification.log', [args.java_home / 'bin/java', '-Xverify:all', '-cp',
                       runtime, 'VerifyTeamMixins', ftb, build])
    report = {'jar': jar.name, 'sha256': hashlib.sha256(jar.read_bytes()).hexdigest(),
              'clientOnly': True, 'ftbTeams': '2001.3.2', 'verification': verification}
    (build / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
