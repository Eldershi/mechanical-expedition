"""Build shared fluid-registry compatibility with Steam Letters and its server variant."""
from pathlib import Path
import argparse,hashlib,json,subprocess,zipfile
parser=argparse.ArgumentParser()
parser.add_argument('--input',type=Path,required=True)
parser.add_argument('--output-dir',type=Path,required=True)
parser.add_argument('--java-home',type=Path,required=True)
parser.add_argument('--asm-root',type=Path,required=True)
args=parser.parse_args()
assert hashlib.sha256(args.input.read_bytes()).hexdigest()=='d7fc6196f18fa4f83148e5b3e50d7b203662405374e40e3a2bcaa99f646e5148'
args.output_dir.mkdir(parents=True,exist_ok=True)
client=args.output_dir/'Create-Steam-Ages-1.0-expedition-steamletters-compat.jar'
with zipfile.ZipFile(args.input) as source,zipfile.ZipFile(client,'w',zipfile.ZIP_DEFLATED) as result:
 for entry in source.infolist():
  data=source.read(entry.filename)
  if entry.filename=='create_steam_ages.mixins.json':
   config=json.loads(data);assert config['mixins']==['BoilerDataMixin'];config['mixins']=[];data=(json.dumps(config,indent=2)+'\n').encode()
  elif entry.filename=='META-INF/mods.toml':
   text=data.decode().replace('version = "1.0"','version = "1.0-expedition-sl-compat2"',1)
   text+='\n[[dependencies."create_steam_ages"]]\nmodId = "steam_letters"\nmandatory = true\nversionRange = "[2.0.1]"\nordering = "AFTER"\nside = "BOTH"\n'
   data=text.encode()
  result.writestr(entry,data)
with zipfile.ZipFile(args.input) as original,zipfile.ZipFile(client) as patched:
 changed=[n for n in original.namelist() if original.read(n)!=patched.read(n)]
 assert set(changed)=={'META-INF/mods.toml','create_steam_ages.mixins.json'}
classes=args.output_dir/'classes';classes.mkdir(exist_ok=True)
cp=':'.join(str(args.asm_root/n/'9.8'/(n+'-9.8.jar')) for n in ['asm','asm-tree'])
source=Path(__file__).resolve().parent/'src/SteamAgesServerPatch.java'
subprocess.run([str(args.java_home/'bin/javac'),'--release','17','-cp',cp,'-d',str(classes),str(source)],check=True)
server=args.output_dir/'server'/client.name;server.parent.mkdir(exist_ok=True)
subprocess.run([str(args.java_home/'bin/java'),'-cp',str(classes)+':'+cp,'SteamAgesServerPatch',str(client),str(server)],check=True)
with zipfile.ZipFile(client) as shared,zipfile.ZipFile(server) as dedicated:
 server_changes=[n for n in shared.namelist() if shared.read(n)!=dedicated.read(n)]
report={'client':client.name,'clientSha256':hashlib.sha256(client.read_bytes()).hexdigest(),
 'server':server.relative_to(args.output_dir).as_posix(),'serverSha256':hashlib.sha256(server.read_bytes()).hexdigest(),
 'steamLetters':'2.0.1','changedClientMembers':changed,'changedServerMembers':server_changes}
(args.output_dir/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
