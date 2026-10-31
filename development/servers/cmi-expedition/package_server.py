"""Freeze the checked server runtime for upload; excludes local validation worlds/logs."""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile
from datetime import datetime
from deployment_mod_overlays import load_mod_overlays, source_for_mod_package, load_server_additions
ROOT=Path(__file__).resolve().parent
SERVER=ROOT/'instance'
CLIENT_ROOT=ROOT.parents[1]/'clients/cmi-expedition'
sys.path.insert(0,str(CLIENT_ROOT/'tools'))
from mod_removal_policy import load_removal_policy, jar_mod_ids, validate_mod_rows
REMOVAL_POLICY=load_removal_policy(CLIENT_ROOT)
OUT=ROOT.parents[1]/'releases/0.2.0-test.1'
SELECTION=json.loads((ROOT/'evidence/mod-selection.json').read_text())
folders=['mods','libraries','config','defaultconfigs','hotai','ldlib','patchouli_books',
         'moonlight-global-datapacks','datapacks','oeb','oei','oef','tlm_custom_pack','kubejs']
allowed_mods={row['file']:row for row in SELECTION['included']}
validate_mod_rows(SELECTION['included'],REMOVAL_POLICY)
actual_mods=sorted((SERVER/'mods').glob('*.jar'))
validate_mod_rows([{'file':path.name,'modIds':jar_mod_ids(path)} for path in actual_mods],REMOVAL_POLICY)
if {path.name for path in actual_mods}!=set(allowed_mods):
    raise ValueError('Server mods differ from the reviewed server selection')
MOD_OVERLAYS=load_mod_overlays(ROOT)
if set(MOD_OVERLAYS)-set(allowed_mods):raise ValueError('Patch manifest contains unselected server mods')
SERVER_ADDITIONS=load_server_additions(ROOT)
def validate_server_additions_for_package(additions, selected, actual):
    actual_by_name={path.name:path for path in actual}
    for name, addition in additions.items():
        entry=selected.get(name)
        target=actual_by_name.get(name)
        if entry is None or target is None:
            raise ValueError('Server addition is missing from selection or instance: ' + name)
        if entry.get('sha256')!=addition['sha256'] or sorted(entry.get('modIds', []))!=sorted(addition['modIds']):
            raise ValueError('Server addition selection differs from manifest: ' + name)
        if hashlib.sha256(target.read_bytes()).hexdigest()!=addition['sha256'] or jar_mod_ids(target)!=jar_mod_ids(addition['blob']):
            raise ValueError('Server addition instance differs from manifest: ' + name)
validate_server_additions_for_package(SERVER_ADDITIONS,allowed_mods,actual_mods)
if set(SERVER_ADDITIONS)&set(MOD_OVERLAYS):raise ValueError('Server addition also registered as a replacement overlay')
output=OUT/'mechanical-expedition-0.2.0-test.1-server.zip'
skip_parts={'logs','saves','crash-reports','exported','client_scripts','probe','__pycache__','.DS_Store'}
def source_for_packaged_file(relative, original):
    if relative.parts[0]=='mods':
        return source_for_mod_package(original,allowed_mods[original.name]['sha256'],MOD_OVERLAYS)
    # Shared client copies must not replace dedicated-server generation settings.
    override=ROOT/'deployment'/relative
    return override if relative.parts[0] in {'config','kubejs'} and override.is_file() else original

rows=[]
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for folder in folders:
        base=SERVER/folder
        if not base.exists():continue
        for p in sorted(base.rglob('*')):
            if not p.is_file() or p.is_symlink():continue
            relative=p.relative_to(SERVER)
            if set(relative.parts)&skip_parts:continue
            name=relative.as_posix()
            if name.startswith('config/chunky/tasks/'):continue
            if folder=='mods' and p.name not in allowed_mods:continue
            source=source_for_packaged_file(relative,p)
            blob=source.read_bytes();digest=hashlib.sha256(blob).hexdigest()
            if folder=='mods':
                expected=MOD_OVERLAYS[p.name]['patchedSha256'] if p.name in MOD_OVERLAYS else allowed_mods[p.name]['sha256']
                assert digest==expected,p.name
            # Explicit deployment settings take precedence over legacy defaults.
            if name=='config/simplebackups-common.toml' and not (ROOT/'deployment'/relative).is_file():
                text=blob.decode().replace('backupsToKeep = 10','backupsToKeep = 6').replace('timer = 120','timer = 60').replace('maxDiskSize = "25 GB"','maxDiskSize = "8 GB"').replace('outputPath = "simplebackups"','outputPath = "simplebackups-expedition"').replace('noPlayerBackups = false','noPlayerBackups = true')
                blob=text.encode();digest=hashlib.sha256(blob).hexdigest()
            z.writestr(name,blob);rows.append({'path':name,'sha256':digest,'bytes':len(blob)})
    generated={'mod-removal-20261018.json':(CLIENT_ROOT/'mod-removal-20261018.json').read_bytes(),
        'user_jvm_args.txt':(ROOT/'deployment/user_jvm_args.txt').read_bytes(),
        'server.properties':(ROOT/'deployment/server.properties').read_bytes(),
        'eula.txt':b'eula=true\n',
        'server.jar':(ROOT/'deployment/server.jar').read_bytes(),
        'server-upstream-20261017.jar':(ROOT/'deployment/server-upstream-20261017.jar').read_bytes(),
        'server-patches.json':(ROOT/'deployment/server-patches.json').read_bytes(),
        'run.sh':(SERVER/'run.sh').read_bytes(),'run.bat':(SERVER/'run.bat').read_bytes(),
        'pack-info.json':(json.dumps({'name':'Mechanical Expedition','version':'0.2.0-test.1',
            'minecraft':'1.20.1','forge':'47.4.10','java':17,'serverMods':len(allowed_mods)},indent=2)+'\n').encode()}
    addition_manifest=ROOT/'deployment/server-additions.json'
    if addition_manifest.is_file():generated['server-additions.json']=addition_manifest.read_bytes()
    for name,blob in generated.items():
        z.writestr(name,blob);rows.append({'path':name,'sha256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob)})
    z.writestr('deployment-files.json',json.dumps(rows,indent=2)+'\n')
with zipfile.ZipFile(output) as z:
    assert z.testzip() is None
    assert len([n for n in z.namelist() if n.startswith('mods/') and n.endswith('.jar')])==len(allowed_mods)
    assert not any(n.startswith(('world/','expedition-local-validation/','logs/')) for n in z.namelist())
report={'builtAt':datetime.now().astimezone().isoformat(),'file':str(output),'bytes':output.stat().st_size,
    'sha256':hashlib.file_digest(output.open('rb'),'sha256').hexdigest(),'serverMods':len(allowed_mods),
    'files':len(rows),'minecraft':'1.20.1','forge':'47.4.10','java':17,
    'newWorld':'expedition','worldsIncluded':False,'zipIntegrityPassed':True,
    'removalPolicySha256':REMOVAL_POLICY['sha256'],
    'panelLauncherVerified':'server-bootstrap-console.log','localServerReady':'run-04-server-ready.log'}
(ROOT/'evidence/server-package.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False,indent=2))
