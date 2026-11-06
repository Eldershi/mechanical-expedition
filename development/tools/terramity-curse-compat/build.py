#!/usr/bin/env python3
"""Build the server combat and spawn compatibility add-on against SRG libraries."""
import argparse,os,subprocess,zipfile,json,hashlib
from pathlib import Path

def build():
    parser=argparse.ArgumentParser();parser.add_argument('--libraries',required=True,type=Path);parser.add_argument('--mods',required=True,type=Path)
    args=parser.parse_args();tool=Path(__file__).resolve().parent;out=tool/'dist';classes=tool/'build/classes';classes.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True)
    libs=args.libraries.resolve()
    mc=list(libs.glob('net/minecraft/server/1.20.1-*/server-*-srg.jar')) or list(libs.glob('net/minecraft/client/1.20.1-*/client-*-srg.jar'))
    deps=mc[:1]
    for relative in ['net/minecraftforge/forge','net/minecraftforge/fmlcore','net/minecraftforge/fmlloader','net/minecraftforge/javafmllanguage','net/minecraftforge/eventbus','net/minecraftforge/forgespi','org/spongepowered/mixin','org/slf4j/slf4j-api','com/mojang/brigadier','com/mojang/datafixerupper','com/mojang/authlib','com/google/guava/guava','com/google/code/gson/gson','it/unimi/dsi/fastutil','org/jetbrains/annotations']:
        deps.extend(p for p in (libs/relative).rglob('*.jar') if zipfile.is_zipfile(p) and not p.name.endswith(('-sources.jar','-extra.jar')))
    deps.extend(args.mods.glob('EnigmaticLegacy-*.jar'));cp=os.pathsep.join(map(str,deps));(tool/'build/classpath.txt').write_text(cp)
    subprocess.run(['javac','--release','17','-proc:none','-encoding','UTF-8','-cp',cp,'-d',str(classes),*map(str,(tool/'src').rglob('*.java'))],check=True)
    artifact=out/'expedition-terramity-curse-compat-1.0.0.jar'
    config={'required':True,'minVersion':'0.8','package':'expedition.terramitycompat.mixin','compatibilityLevel':'JAVA_17','mixins':['ShadowflameDamageMixin','ShadowflameFeedbackMixin'],'injectors':{'defaultRequire':1}}
    toml='modLoader="javafml"\nloaderVersion="[47,)"\nlicense="All Rights Reserved"\n[[mods]]\nmodId="expedition_terramity_curse_compat"\nversion="1.0.0"\ndisplayName="Expedition Terramity Curse Compatibility"\ndisplayTest="IGNORE_ALL_VERSION"\ndescription="Shadowflame player attribution and Terramity natural spawn rules."\n'
    for mod,version in [('minecraft','[1.20.1,1.20.2)'),('terramity','[0.9.8]'),('enigmaticlegacy','[2.30.1]')]:
        toml+=f'[[dependencies.expedition_terramity_curse_compat]]\nmodId="{mod}"\nmandatory=true\nversionRange="{version}"\nside="BOTH"\n'
    with zipfile.ZipFile(artifact,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\r\nMixinConfigs: expedition-terramity-curse-compat.mixins.json\r\n\r\n');z.writestr('META-INF/mods.toml',toml)
        z.writestr('expedition-terramity-curse-compat.mixins.json',json.dumps(config));z.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Terramity curse compatibility'}}))
        for p in classes.rglob('*.class'):z.write(p,p.relative_to(classes).as_posix())
    print(artifact.name,hashlib.sha256(artifact.read_bytes()).hexdigest())
if __name__=='__main__':build()
