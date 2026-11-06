#!/usr/bin/env python3
"""Build/test an additive shared-server world-age guard, changing no installed files."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,zipfile
TOOL=Path(__file__).resolve().parent
ROOT=TOOL.parents[1]
OUT=TOOL/'dist'
BUILD=TOOL/'build'
CLASSES=BUILD/'classes'
LIBS=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
SPELL=None
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def run(args,name):
    result=subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=60,cwd=BUILD)
    (BUILD/name).write_text(result.stdout+result.stderr)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)
    return result.stdout+result.stderr
def member(z,name,data):
    info=zipfile.ZipInfo(name,(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o100644<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,data)
def main():
    global SPELL, OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--spell', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, default=OUT)
    args=parser.parse_args()
    SPELL=args.spell.resolve();OUT=args.output_dir.resolve()
    for folder in [CLASSES,OUT,BUILD/'validation-classes',BUILD/'fixture-classes',BUILD/'service-source']:
        folder.mkdir(parents=True,exist_ok=True)
    original_hash=sha(SPELL)
    # Official all.jar is a wrapper; runtime worldgen classes live in its embedded mod.
    with zipfile.ZipFile(SPELL) as archive:
        spell_runtime=BUILD/'maidspell-mod.jar'
        spell_runtime.write_bytes(archive.read('META-INF/maidspell/maidspell-mod.jar'))
    deps=[LIBS/'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar',
          LIBS/'org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar',spell_runtime]
    for rel in ['net/minecraftforge/forge/1.20.1-47.4.10','net/minecraftforge/fmlcore/1.20.1-47.4.10',
      'net/minecraftforge/fmlloader/1.20.1-47.4.10','net/minecraftforge/eventbus','org/slf4j/slf4j-api/2.0.1',
      'com/mojang/brigadier/1.1.8','com/mojang/datafixerupper/6.0.8','com/google/guava/guava/31.1-jre',
      'com/google/code/gson/gson/2.10','it/unimi/dsi/fastutil/8.5.9','org/jetbrains/annotations']:
        deps.extend(p for p in (LIBS/rel).rglob('*.jar') if zipfile.is_zipfile(p))
    asm=[LIBS/f'org/ow2/asm/{name}/9.8/{name}-9.8.jar' for name in ['asm','asm-tree','asm-util','asm-analysis','asm-commons']]
    cp=os.pathsep.join(map(str,deps+asm))
    run(['javac','--release','17','-proc:none','-encoding','UTF-8','-cp',cp,'-d',CLASSES,*sorted((TOOL/'src').rglob('*.java'))],'compile.log')
    jar=OUT/'expedition-maid-worldgen-guard-1.0.1.jar'
    config={'required':True,'minVersion':'0.8','package':'expedition.maidguard.mixin','compatibilityLevel':'JAVA_17',
      'mixins':['StellarEndshoreStartupGuard'],'injectors':{'defaultRequire':1}}
    with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
        member(z,'META-INF/MANIFEST.MF','Manifest-Version: 1.0\r\nMixinConfigs: expedition-maid-worldgen-guard.mixins.json\r\n\r\n')
        member(z,'META-INF/mods.toml','''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_maid_worldgen_guard"
version="1.0.1"
displayName="Expedition Maid Existing World Guard"
displayTest="IGNORE_ALL_VERSION"
description="Prevent Maid Spell startup fixed placement when overworld gameTime is greater than zero. Dedicated and integrated servers."
[[dependencies.expedition_maid_worldgen_guard]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
side="BOTH"
[[dependencies.expedition_maid_worldgen_guard]]
modId="touhou_little_maid_spell"
mandatory=true
versionRange="[1.9.3.2-forge+mc1.20.1]"
side="BOTH"
''')
        member(z,'pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Maid Spell existing-world startup guard'}}))
        member(z,'expedition-maid-worldgen-guard.mixins.json',json.dumps(config))
        for path in sorted((CLASSES/'expedition').rglob('*.class')):member(z,path.relative_to(CLASSES).as_posix(),path.read_bytes())
    services=ROOT/'tools/stock-keeper-tooltip-fix/validation'
    for name in ['StandaloneMixinService.java','StandaloneProperties.java']:
        text=(services/name).read_text().replace('return "CLIENT";','return "SERVER";')
        (BUILD/'service-source'/name).write_text(text)
    validation=BUILD/'validation-classes'
    validation_cp=os.pathsep.join([str(jar),cp])
    run(['javac','--release','17','-proc:none','-cp',validation_cp,'-d',validation,
       *sorted((TOOL/'validation').glob('*.java')),*sorted((BUILD/'service-source').glob('*.java'))],'validation-compile.log')
    service_folder=validation/'META-INF/services';service_folder.mkdir(parents=True,exist_ok=True)
    (service_folder/'org.spongepowered.asm.service.IMixinService').write_text('StandaloneMixinService\n')
    (service_folder/'org.spongepowered.asm.service.IGlobalPropertyService').write_text('StandaloneProperties\n')
    apply=run(['java','-Xverify:all','-Xmx768m','-cp',str(validation)+os.pathsep+validation_cp,
      'ApplyGuardMixin',spell_runtime,BUILD/'StellarEndshoreFixedSpawn.transformed.class',BUILD/'fixture-classes'],'mixin-application.log')
    fixture=BUILD/'fixture-classes'
    test_deps=[LIBS/'org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar',LIBS/'org/slf4j/slf4j-api/2.0.1/slf4j-api-2.0.1.jar']
    for name in ['log4j-api','log4j-core','log4j-slf4j2-impl']:test_deps.append(LIBS/f'org/apache/logging/log4j/{name}/2.19.0/{name}-2.19.0.jar')
    test_cp=os.pathsep.join(map(str,[fixture,jar,*test_deps]))
    run(['javac','--release','17','-proc:none','-cp',test_cp,'-d',fixture,*sorted((TOOL/'tests').rglob('*.java'))],'fixture-compile.log')
    log_config=BUILD/'test-log4j2.xml'
    log_config.write_text('<Configuration><Appenders><Console name="Console" target="SYSTEM_OUT"><PatternLayout pattern="%level %msg%n"/></Console></Appenders><Loggers><Root level="info"><AppenderRef ref="Console"/></Root></Loggers></Configuration>')
    regression=run(['java','-Xverify:all','-Dlog4j.configurationFile='+str(log_config),'-cp',test_cp,'MaidGuardRegression'],'regression.log')
    assert regression.count('[MaidWorldgenGuard] Blocked')==4,regression
    assert sha(SPELL)==original_hash
    report={'jar':str(jar),'sha256':sha(jar),'officialSpellJarUnchanged':True,'officialSpellSha256':original_hash,
      'activeClientModified':False,'onlineServerModified':False,'commonServerMixin':True,
      'policy':'Cancel onServerStarted at HEAD iff overworld.getGameTime()>0; preserve time0 original scheduling',
      'realMixinApplication':apply.strip(),'transformedCallbackRegression':regression.strip(),
      'packFormat':15,'displayTest':'IGNORE_ALL_VERSION','existingMarkerWrites':False,'naturalChunkGenerationModified':False,
      'limitation':'Actual offline Mixin transform plus transformed callback scheduling fixtures; full Forge launch in an existing world is separate validation.'}
    (OUT/'worldgen-guard-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (OUT/'worldgen-guard-SHA256SUMS.txt').write_text(sha(jar)+'  '+jar.name+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
