"""Build a minimal, reviewable compatibility guard without modifying upstream jars."""
from pathlib import Path
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LIBS = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
source = ROOT / 'tools/compat/ChunkyStartupGuard.java'
classes = ROOT / 'evidence/optimization/chunky-guard-classes'
classes.mkdir(parents=True, exist_ok=True)
chunky = ROOT / 'disabled-mods/optimization-alternatives/Chunky-1.3.146.jar'
if not chunky.exists(): chunky = ROOT / 'instance/mods/Chunky-1.3.146.jar'
libraries = [chunky, *list((LIBS / 'org/spongepowered/mixin').rglob('*.jar'))]
assert len(libraries) > 1, 'Missing installed Mixin runtime'
result = subprocess.run(['javac','--release','17','-proc:none','-encoding','UTF-8','-cp',':'.join(map(str,libraries)),'-d',str(classes),str(source)],capture_output=True,text=True)
(ROOT / 'evidence/optimization/chunky-guard-compile.log').write_text(result.stdout + result.stderr)
assert result.returncode == 0, result.stderr
jar = ROOT / 'downloads/optimization/expedition-chunky-startup-guard-1.0.0.jar'
with zipfile.ZipFile(jar,'w',zipfile.ZIP_DEFLATED) as output:
    output.writestr('META-INF/MANIFEST.MF','Manifest-Version: 1.0\nMixinConfigs: expedition-chunky-guard.mixins.json\n\n')
    output.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':15,'description':'Expedition DH / Chunky startup compatibility'}}))
    output.writestr('META-INF/mods.toml','''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_chunky_guard"
version="1.0.0"
displayName="Expedition DH / Chunky Startup Guard"
[[dependencies.expedition_chunky_guard]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
[[dependencies.expedition_chunky_guard]]
modId="distanthorizons"
mandatory=true
versionRange="[3.3.3]"
[[dependencies.expedition_chunky_guard]]
modId="chunky"
mandatory=true
versionRange="[1.3.146]"
''')
    output.writestr('expedition-chunky-guard.mixins.json',json.dumps({'required':True,'minVersion':'0.8','package':'expedition.compat','compatibilityLevel':'JAVA_17','mixins':['ChunkyStartupGuard'],'injectors':{'defaultRequire':1}}))
    for file in classes.rglob('*.class'): output.write(file,str(file.relative_to(classes)))
print(json.dumps({'built':str(jar),'status':'pending runtime validation; not installed yet'}))
