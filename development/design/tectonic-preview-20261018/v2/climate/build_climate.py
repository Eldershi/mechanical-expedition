"""Compile the isolated v2 alpine compatibility mod; no installation or launch."""
from pathlib import Path
import importlib.util
import json
import subprocess
import zipfile

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
spec=importlib.util.spec_from_file_location('terrain_cp',PROJECT/'design/newsteam-worldgen-test/tools/terrainlab_classpath.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
server_libraries=PROJECT/'servers/cmi-expedition/instance/libraries'
launcher_libraries=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
paths=[launcher_libraries/path.relative_to(server_libraries) if path.is_relative_to(server_libraries) else path for path in module.classpath(client=True)]
paths=[path for path in paths if path.is_file()]
for module_name in ['javafmllanguage','fmlcore','fmlloader']:
    paths.extend((launcher_libraries/'net/minecraftforge'/module_name/'1.20.1-47.4.10').glob('*.jar'))
classes=HERE/'build/classes';classes.mkdir(parents=True,exist_ok=True)
result=subprocess.run(['/Library/Java/JavaVirtualMachines/jdk-17.0.5.jdk/Contents/Home/bin/javac',
    '--release','17','-proc:none','-encoding','UTF-8','-cp',':'.join(map(str,paths)),
    '-d',str(classes),*map(str,(HERE/'src').rglob('*.java'))],capture_output=True,text=True)
(HERE/'build/compile.log').write_text(result.stdout+result.stderr)
if result.returncode:
    print(result.stdout+result.stderr);raise SystemExit(result.returncode)
jar=HERE/'build/expedition-alpine-climate-1.0.0.jar'
with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\nMixinConfigs: expedition-alpine.mixins.json\n\n')
    archive.writestr('META-INF/mods.toml','''modLoader="javafml"
loaderVersion="[47,)"
license="Private local preview compatibility"
[[mods]]
modId="expedition_alpine_climate"
version="1.0.0"
displayName="Expedition Local Alpine Climate"
[[dependencies.expedition_alpine_climate]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
''')
    archive.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Local alpine climate policy for isolated v2 preview'}}))
    archive.writestr('expedition-alpine.mixins.json',json.dumps({'required':True,'minVersion':'0.8','package':'expedition.alpine.mixin','compatibilityLevel':'JAVA_17','mixins':['BiomeTemperatureMixin','BiomeTemperatureAccess','SurfaceSystemMixin'],'injectors':{'defaultRequire':1}}))
    archive.write(HERE/'biome-policy.json','alpine-biome-policy.json')
    for path in classes.rglob('*.class'):archive.write(path,path.relative_to(classes).as_posix())
print(json.dumps({'jar':str(jar),'installed':False,'launched':False}))
