#!/usr/bin/env python3
"""Reproduce the original Mixin error and transform the frozen compatibility candidate."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import zipfile

TOOL=Path(__file__).resolve().parent
ROOT=TOOL.parents[1]
INSTANCE=(Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
LIBS=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
BUILD=TOOL/'build/validation'
JAVA=Path('/Library/Java/JavaVirtualMachines/jdk-17.0.5.jdk/Contents/Home/bin')
NAME='1.20.1-maid_storage_manager-1.15.6.jar'

def run(args,log,timeout=60):
    p=subprocess.run(list(map(str,args)),text=True,capture_output=True,timeout=timeout,cwd=BUILD)
    output=p.stdout+p.stderr
    (BUILD/log).write_text(output)
    return p.returncode,output

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',type=Path,default=ROOT/'releases/maid-jei-compat-20261027/payload/mods'/NAME)
    args=parser.parse_args()
    candidate=args.candidate.resolve()
    original=ROOT/'releases/maid-addons-20261027/payload/mods'/NAME
    assert candidate.is_file(),candidate
    original_sha=hashlib.sha256(original.read_bytes()).hexdigest()
    frozen=hashlib.sha256(candidate.read_bytes()).hexdigest()
    classes=BUILD/'classes';classes.mkdir(parents=True,exist_ok=True)
    vanilla=LIBS/'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar'
    deps=[vanilla,LIBS/'org/spongepowered/mixin/0.8.5/mixin-0.8.5.jar']
    server_libs=ROOT/'servers/cmi-expedition/instance/libraries'
    with zipfile.ZipFile(server_libs/'net/minecraft/server/1.20.1/server-1.20.1.jar') as z:
        for line in z.read('META-INF/libraries.list').decode().splitlines():
            if line.strip():
                relative=line.split('\t')[2]
                jar=LIBS/relative
                if not zipfile.is_zipfile(jar):jar=server_libs/relative
                if zipfile.is_zipfile(jar):deps.append(jar)
    for name in ['asm','asm-tree','asm-analysis','asm-util','asm-commons']:
        deps.append(LIBS/f'org/ow2/asm/{name}/9.8/{name}-9.8.jar')
    deps.extend(p for p in sorted((INSTANCE/'mods').glob('*.jar')) if p.name!=NAME)
    deps.extend(sorted((LIBS/'net/minecraftforge').glob('**/*1.20.1*47.4.10*.jar')))
    cp=os.pathsep.join(map(str,deps))
    code,output=run([JAVA/'javac','--release','17','-proc:none','-cp',cp,'-d',classes,*sorted((TOOL/'validation').glob('*.java'))],'compile.log')
    assert code==0,output
    services=classes/'META-INF/services';services.mkdir(parents=True,exist_ok=True)
    (services/'org.spongepowered.asm.service.IMixinService').write_text('StandaloneMixinService\n')
    (services/'org.spongepowered.asm.service.IGlobalPropertyService').write_text('StandaloneProperties\n')
    config={'required':True,'minVersion':'0.8','package':'studio.fantasyit.maid_storage_manager.mixin','compatibilityLevel':'JAVA_17','mixins':['JeiGuiIconToggleButtonAccessor','JEIRecipeTransferHook'],'injectors':{'defaultRequire':1}}
    (classes/'maid-jei-validation.mixins.json').write_text(json.dumps(config))
    jei=INSTANCE/'mods/jei-1.20.1-forge-15.59.0.212.jar'
    result={}
    for label,jar in [('baseline',original),('candidate',candidate)]:
        destination=BUILD/label;destination.mkdir(exist_ok=True)
        code,output=run([JAVA/'java','-Xverify:all','-Xmx768m','-cp',str(classes)+os.pathsep+str(jar)+os.pathsep+cp,'ApplyJeiMixin',jei,destination],label+'.log')
        result[label]={'exitCode':code,'output':output.strip()}
    assert result['baseline']['exitCode']!=0 and '@Shadow field onClose was not located' in result['baseline']['output'],result['baseline']['output']
    report={'baselineSha256':original_sha,'candidateSha256':frozen,'jeiSha256':hashlib.sha256(jei.read_bytes()).hexdigest(),'actualMixinTransformerApplied':True,'candidateSuccess':result['candidate']['exitCode']==0,'mixinVersion':'0.8.5','minecraftStarted':False,'activeInstanceModified':False,'configurationScope':'Exact candidate hook and accessor; optional Forge plugin omitted in isolated service','limitation':'Confirms target transformation and ASM basic verification; does not prove live GUI interaction or other pack mixins.','results':result}
    assert frozen==hashlib.sha256(candidate.read_bytes()).hexdigest()
    (BUILD/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    assert report['candidateSuccess'],'See candidate.log for compatibility failure'

if __name__=='__main__':main()
