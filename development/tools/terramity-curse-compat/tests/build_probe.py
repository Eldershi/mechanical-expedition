#!/usr/bin/env python3
"""Build a disposable runtime probe; install it only in a test server."""
import argparse,json,os,subprocess,zipfile
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--mods',required=True,type=Path)
parser.add_argument('--output',required=True,type=Path)
args=parser.parse_args()
tool=Path(__file__).resolve().parents[1]
classpath=(tool/'build/classpath.txt').read_text()+os.pathsep+os.pathsep.join(map(str,[
    tool/'dist/expedition-terramity-curse-compat-1.0.0.jar',
    *args.mods.glob('curios-forge-*.jar'),*args.mods.glob('terramity-*.jar')]))
classes=tool/'build/probe-classes';classes.mkdir(exist_ok=True)
subprocess.run(['javac','--release','17','-proc:none','-cp',classpath,'-d',str(classes),str(tool/'tests/RuntimeVerification.java')],check=True)
args.output.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('META-INF/mods.toml','modLoader="javafml"\nloaderVersion="[47,)"\nlicense="All Rights Reserved"\n[[mods]]\nmodId="expedition_terramity_runtime_probe"\nversion="1.0"\ndisplayName="Terramity runtime verification"\n')
    archive.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Runtime verification'}}))
    for path in classes.rglob('*.class'):archive.write(path,path.relative_to(classes).as_posix())
print(args.output)
