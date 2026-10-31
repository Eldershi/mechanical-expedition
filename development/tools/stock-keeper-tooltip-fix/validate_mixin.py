#!/usr/bin/env python3
"""Read the frozen candidate and apply its real Mixin without starting Minecraft."""
from pathlib import Path
import hashlib, json, os, subprocess, zipfile

TOOL=Path(__file__).resolve().parent
ROOT=TOOL.parents[1]
INSTANCE=(Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
LIBS=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
OUT=ROOT/'releases/bugfix-bundle-20261027/storage-fix'
BUILD=TOOL/'build/mixin-validation'
CLASSES=BUILD/'classes'
FROZEN='6e433479de30c59987305c572b1f011e8c87f6e7913073dfee7237d66c541953'

def run(args,log,timeout=60):
    result=subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=timeout,cwd=BUILD)
    (BUILD/log).write_text(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError(result.stdout+result.stderr)
    return result.stdout+result.stderr

def main():
    CLASSES.mkdir(parents=True,exist_ok=True)
    candidate=OUT/'expedition-stock-keeper-tooltip-fix-1.0.0.jar'
    assert hashlib.sha256(candidate.read_bytes()).hexdigest()==FROZEN
    create=INSTANCE/'mods/create-1.20.1-6.0.8.jar'
    vanilla=LIBS/'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar'
    deps=[candidate,create,vanilla,LIBS/'org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar']
    server_libs=ROOT/'servers/cmi-expedition/instance/libraries'
    with zipfile.ZipFile(server_libs/'net/minecraft/server/1.20.1/server-1.20.1.jar') as z:
        for line in z.read('META-INF/libraries.list').decode().splitlines():
            if not line.strip(): continue
            relative=line.split('\t')[2]
            jar=LIBS/relative
            if not zipfile.is_zipfile(jar): jar=server_libs/relative
            if zipfile.is_zipfile(jar): deps.append(jar)
    for name in ['asm','asm-tree','asm-analysis','asm-util','asm-commons']:
        deps.append(LIBS/f'org/ow2/asm/{name}/9.8/{name}-9.8.jar')
    with zipfile.ZipFile(create) as z:
        for name in z.namelist():
            if name.endswith('.jar'):
                destination=BUILD/Path(name).name
                destination.write_bytes(z.read(name));deps.append(destination)
    cp=os.pathsep.join(map(str,deps))
    run(['javac','--release','17','-proc:none','-cp',cp,'-d',CLASSES,*sorted((TOOL/'validation').glob('*.java'))],'compile.log')
    services=CLASSES/'META-INF/services';services.mkdir(parents=True,exist_ok=True)
    (services/'org.spongepowered.asm.service.IMixinService').write_text('StandaloneMixinService\n')
    (services/'org.spongepowered.asm.service.IGlobalPropertyService').write_text('StandaloneProperties\n')
    result=run(['java','-Xverify:all','-Xmx768m','-cp',str(CLASSES)+os.pathsep+cp,'ApplyRealMixin',create,BUILD/'StockKeeperRequestScreen.transformed.class'],'apply.log')
    assert hashlib.sha256(candidate.read_bytes()).hexdigest()==FROZEN
    report={'frozenCandidateSha256':FROZEN,'candidateRebuilt':False,'actualMixinTransformerApplied':True,
        'mixinVersion':'0.8.5','environment':'Standalone read-only classpath service, client side',
        'minecraftOrForgeStarted':False,'liveGameScreenConfirmed':False,'result':result.strip(),
        'transformedClass':str(BUILD/'StockKeeperRequestScreen.transformed.class'),
        'limitation':'This runs the actual Mixin transformer, but does not prove the live game loaded the StockKeeper screen or completed a delivery.'}
    (OUT/'mixin-application-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
