#!/usr/bin/env python3
"""Build an optional server-side add-on; never edit an installed instance."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import zipfile

TOOL = Path(__file__).resolve().parent
PROJECT = TOOL.parents[1]
LIBS = PROJECT / 'servers/cmi-expedition/instance/libraries'
META_LIBS = Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries'
BUILD = TOOL / 'build'
CLASSES = BUILD / 'classes'
OUT = TOOL / 'dist'
MC = LIBS / 'net/minecraft/server/1.20.1-20230612.114412/server-1.20.1-20230612.114412-srg.jar'


def run(args, log):
    result = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=60, cwd=BUILD)
    (BUILD / log).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout + result.stderr


def member(archive, name, value):
    entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    entry.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(entry, value)


def main():
    for directory in (BUILD, CLASSES, OUT, BUILD / 'validation-classes', BUILD / 'service-source'):
        directory.mkdir(parents=True, exist_ok=True)
    relative_dependencies = [
        'net/minecraftforge/forge/1.20.1-47.4.10',
        'net/minecraftforge/fmlcore/1.20.1-47.4.10',
        'net/minecraftforge/fmlloader/1.20.1-47.4.10',
        'net/minecraftforge/eventbus/6.0.5',
        'org/spongepowered/mixin/0.8.5', 'org/slf4j/slf4j-api/2.0.1',
        'com/mojang/brigadier/1.1.8', 'com/mojang/datafixerupper/6.0.8',
        'com/google/guava/guava/31.1-jre', 'com/google/code/gson/gson/2.10',
        'it/unimi/dsi/fastutil/8.5.9', 'org/jetbrains/annotations',
    ]
    dependencies = [MC]
    for relative in relative_dependencies:
        root = LIBS if (LIBS / relative).exists() else META_LIBS
        dependencies.extend(sorted(path for path in (root / relative).rglob('*.jar') if zipfile.is_zipfile(path)))
    for name in ('asm', 'asm-tree', 'asm-util', 'asm-analysis', 'asm-commons'):
        relative = f'org/ow2/asm/{name}/9.8/{name}-9.8.jar'
        dependencies.append((LIBS if (LIBS / relative).exists() else META_LIBS) / relative)
    classpath = os.pathsep.join(map(str, dependencies))
    run(['javac', '--release', '17', '-proc:none', '-encoding', 'UTF-8', '-cp', classpath,
         '-d', CLASSES, *sorted((TOOL / 'src').rglob('*.java'))], 'compile.log')
    artifact = OUT / 'expedition-player-motion-guard-1.0.0.jar'
    mixins = {'required': True, 'minVersion': '0.8', 'package': 'expedition.motionguard.mixin',
              'compatibilityLevel': 'JAVA_17', 'mixins': ['PlayerMotionMixin'],
              'injectors': {'defaultRequire': 1}}
    with zipfile.ZipFile(artifact, 'w', zipfile.ZIP_DEFLATED) as archive:
        member(archive, 'META-INF/MANIFEST.MF',
               'Manifest-Version: 1.0\r\nMixinConfigs: expedition-player-motion-guard.mixins.json\r\n\r\n')
        member(archive, 'META-INF/mods.toml', '''modLoader="lowcodefml"
loaderVersion="[47,)"
license="All Rights Reserved"
[[mods]]
modId="expedition_player_motion_guard"
version="1.0.0"
displayName="Expedition Player Motion Guard"
displayTest="IGNORE_ALL_VERSION"
description="Reject non-finite, unrepresentable or excessive player collision queries and record their caller."
[[dependencies.expedition_player_motion_guard]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
side="SERVER"
''')
        member(archive, 'pack.mcmeta', json.dumps({'pack': {'pack_format': 15,
               'description': 'Server player collision query guard'}}))
        member(archive, 'expedition-player-motion-guard.mixins.json', json.dumps(mixins, sort_keys=True))
        for path in sorted((CLASSES / 'expedition').rglob('*.class')):
            member(archive, path.relative_to(CLASSES).as_posix(), path.read_bytes())
    validation = BUILD / 'validation-classes'
    for name in ('StandaloneMixinService.java', 'StandaloneProperties.java'):
        source = (PROJECT / 'tools/stock-keeper-tooltip-fix/validation' / name).read_text()
        (BUILD / 'service-source' / name).write_text(source.replace('return "CLIENT";', 'return "SERVER";'))
    validation_cp = str(artifact) + os.pathsep + classpath
    run(['javac', '--release', '17', '-proc:none', '-cp', validation_cp, '-d', validation,
         *sorted((TOOL / 'validation').glob('*.java')),
         *sorted((BUILD / 'service-source').glob('*.java')),
         *sorted((TOOL / 'tests').glob('*.java'))], 'validation-compile.log')
    services = validation / 'META-INF/services'
    services.mkdir(parents=True, exist_ok=True)
    (services / 'org.spongepowered.asm.service.IMixinService').write_text('StandaloneMixinService\n')
    (services / 'org.spongepowered.asm.service.IGlobalPropertyService').write_text('StandaloneProperties\n')
    test_cp = str(validation) + os.pathsep + validation_cp
    policy = run(['java', '-Xverify:all', '-cp', test_cp, 'MotionPolicyTest'], 'policy-test.log')
    transform = run(['java', '-Xverify:all', '-Xmx768m', '-cp', test_cp, 'ApplyMotionMixin',
                     MC, BUILD / 'Entity.transformed.class'], 'mixin-application.log')
    order_config = {'required': True, 'minVersion': '0.8',
                    'package': 'com.github.alexmodguy.alexscaves.mixin',
                    'compatibilityLevel': 'JAVA_17', 'priority': 1000,
                    'refmap': 'alexscaves.refmap.json', 'mixins': ['EntityMixin'],
                    'injectors': {'defaultRequire': 1}}
    (validation / 'alexscaves-entity-order-test.mixins.json').write_text(json.dumps(order_config))
    mods = PROJECT / 'servers/cmi-expedition/instance/mods'
    order_cp = test_cp + os.pathsep + os.pathsep.join(map(str, [
        mods / 'alexscaves-2.0.2.jar', mods / 'citadel-2.6.3-1.20.1.jar']))
    order = run(['java', '-Xverify:all', '-Xmx768m', '-cp', order_cp, 'CheckAlexCavesOrder',
                 MC, BUILD / 'Entity.with-alexscaves.class'], 'alexscaves-order.log')
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    report = {'artifact': artifact.name, 'sha256': digest,
              'policyBoundaries': policy.strip(), 'realTargetMixin': transform.strip(),
              'alexCavesInjectionOrder': order.strip(),
              'installedFilesModified': False,
              'limitation': 'Offline policy and actual Entity Mixin validation; full Forge runtime acceptance is separate.'}
    (OUT / 'verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'SHA256SUMS.txt').write_text(digest + '  ' + artifact.name + '\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
