"""Build the optional Twilight special-placement adapter; does not install it."""
from pathlib import Path
import argparse, json, subprocess, zipfile, shutil
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--instance', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args=parser.parse_args()
LIBS=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
classes=ROOT/'evidence/optimization/worldgen-compat-classes'
if classes.exists():shutil.rmtree(classes)
classes.mkdir(parents=True,exist_ok=True)
libraries=[next((args.instance/'mods').glob('twilightforest*.jar')),LIBS/'net/minecraft/client/1.20.1-20230612.114412/client-1.20.1-20230612.114412-srg.jar']
libraries.append(next((args.instance/'mods').glob('BCLib-20.0.16-forge.jar')))
for name in ['org/spongepowered/mixin','com/google/code/gson','com/google/guava','com/mojang/datafixerupper']:
 libraries.extend((LIBS/name).rglob('*.jar'))
sources=[ROOT/'tools/compat/BossDensityPolicy.java',ROOT/'tools/compat/TwilightBossDensity.java',ROOT/'tools/compat/TwilightMapDensity.java',ROOT/'tools/compat/FrostyardEarlyBiomeCheck.java',ROOT/'tools/compat/TwilightSavedMapDensity.java']
sources.append(ROOT/'tools/compat/BclibBiomePickerInit.java')
sources.append(ROOT/'tools/compat/BclibSourceInit.java')
res=subprocess.run(['javac','--release','17','-proc:none','-encoding','UTF-8','-cp',':'.join(map(str,libraries)),'-d',str(classes),*map(str,sources)],capture_output=True,text=True)
(ROOT/'evidence/optimization/worldgen-compat-compile.log').write_text(res.stdout+res.stderr)
assert res.returncode==0,res.stderr
jar=args.output
jar.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as z:
 z.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\nMixinConfigs: expedition-worldgen.mixins.json\n\n')
 z.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Expedition special boss placement adapter'}}))
 z.writestr('expedition-worldgen.mixins.json',json.dumps({'required':True,'minVersion':'0.8','package':'expedition.worldgen.mixin','compatibilityLevel':'JAVA_17','mixins':['TwilightBossDensity','TwilightMapDensity','TwilightSavedMapDensity','FrostyardEarlyBiomeCheck','BclibBiomePickerInit','BclibSourceInit'],'injectors':{'defaultRequire':1}}))
 z.writestr('META-INF/mods.toml','''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_worldgen_compat"
version="1.0.3"
displayName="Expedition special boss placement adapter"
[[dependencies.expedition_worldgen_compat]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
[[dependencies.expedition_worldgen_compat]]
modId="twilightforest"
mandatory=true
versionRange="[4.3.2508]"
[[dependencies.expedition_worldgen_compat]]
modId="structurify"
mandatory=true
versionRange="[2.0.43]"
[[dependencies.expedition_worldgen_compat]]
modId="bclib"
mandatory=false
versionRange="[20.0.16]"
''')
 for p in classes.rglob('*.class'):z.write(p,str(p.relative_to(classes)))
print(json.dumps({'built':str(jar),'status':'BUILT'}))
