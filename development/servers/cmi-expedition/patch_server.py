"""Apply the dedicated-only Steam Ages rendering fix to a stopped server."""
from pathlib import Path
import hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
SERVER=ROOT/'instance'
LIBS=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries/org/ow2/asm')
cp=':'.join(str(LIBS/folder/'9.8'/f'{folder}-9.8.jar') for folder in ['asm','asm-tree'])
classes=ROOT/'evidence/patch-classes';classes.mkdir(exist_ok=True)
subprocess.run(['javac','--release','17','-cp',cp,'-d',str(classes),str(ROOT/'SteamAgesServerPatch.java')],check=True)
source=PROJECT/'clients/cmi-expedition/instance/mods/Create-Steam-Ages-1.0.jar'
target=ROOT/'downloads/Create-Steam-Ages-1.0-server-fixed.jar'
subprocess.run(['java','-cp',str(classes)+':'+cp,'SteamAgesServerPatch',str(source),str(target)],check=True)
shutil.copy2(target,SERVER/'mods'/source.name)
report={'sourceFile':source.name,'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'serverSha256':hashlib.sha256(target.read_bytes()).hexdigest(),
    'scope':'Server only: remove two RenderType supplier creation/calls and associated private lambdas; retain all common fluid, item, tag and property registrations. Client JAR unchanged.',
    'removedClientOnlyMod':'create_cyber_goggles'}
(ROOT/'evidence/server-mod-fixes.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
p=ROOT/'evidence/mod-selection.json';d=json.loads(p.read_text())
for row in list(d['included']):
    if 'create_cyber_goggles' in row['modIds']:
        d['included'].remove(row);d['excluded'].append({**row,'reason':'Client HUD; eager config references Screen on dedicated server.'})
        jar=SERVER/'mods'/row['file']
        if jar.exists():shutil.move(jar,ROOT/'downloads'/jar.name)
row=next(r for r in d['included'] if r['file']==source.name)
row.setdefault('upstreamSha256',row['sha256']);row['sha256']=report['serverSha256'];row['patch']='server-mod-fixes.json'
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
print('Dedicated server now contains',len(d['included']),'mods')
