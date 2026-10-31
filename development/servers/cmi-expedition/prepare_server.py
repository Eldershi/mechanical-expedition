"""Build the dedicated server from the verified Expedition client, without worlds."""
from pathlib import Path
import hashlib, io, json, shutil, sys, tomllib, zipfile
from patch_mutantmore_server import patch_server_jar
from deployment_mod_overlays import load_mod_overlays, apply_mod_overlay, load_server_additions

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[1]
CLIENT=PROJECT/'clients/cmi-expedition/instance'
SERVER=ROOT/'instance'
sys.path.insert(0,str(CLIENT.parent/'tools'))
from mod_removal_policy import load_removal_policy, jar_mod_ids, is_removed, validate_mod_rows
CLIENT_ONLY=set('''betteradvancements ctm controlling customwindowtitle distanthorizons enchdesc imblocker
immediatelyfast jei_mekanism_multiblocks mousetweaks nerb prism quark_ponders searchables tconplanner
untranslateditems achievement_toast ae2ct just_enough_crafting_tree appleskin asteorbar betterfpsdist
catalogue colorwheel_patcher colorwheel oculus configured drippyloadingscreen dynamic_fps embeddium rubidium
entityculling expedition_ponder_ui expedition_chunky_guard fancymenu ftbxaerocompat jecharacters jei_plus_plus jeiintegration
leawind_third_person mekagenjei mekanism_ponders melody modelfix modernui nolijium
notenoughcrashes quick_pack tslatentitystatus xaerominimap xaeroworldmap embeddium_extra create_cyber_goggles certain_questing_additions'''.split())
# Interlocked 1.1's common right-click handlers read a client KeyMapping. It has no
# content registries/channels; omit the broken bulk-encasing feature on dedicated servers.
CLIENT_ONLY.add('interlocked')
CLIENT_ONLY.update({'culllessleaves', 'expedition_client_performance', 'renderscale'})
FOLDERS=['config','defaultconfigs','hotai','ldlib','patchouli_books','moonlight-global-datapacks',
         'datapacks','oeb','oei','oef','tlm_custom_pack']
SKIP_CONFIG={'fancymenu','paxi/resourcepacks','touhou_little_maid/sites','resourceful-config-web.json'}
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def metadata(blob,nested=False):
    rows=[]
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        if 'META-INF/mods.toml' in z.namelist():
            d=tomllib.loads(z.read('META-INF/mods.toml').decode())
            rows.append({'ids':[m['modId'] for m in d.get('mods',[])],'dependencies':d.get('dependencies',{}),'nested':nested})
        if 'META-INF/jarjar/metadata.json' in z.namelist():
            for jar in json.loads(z.read('META-INF/jarjar/metadata.json'))['jars']:
                path=jar['path']
                if path in z.namelist():rows.extend(metadata(z.read(path),True))
    return rows
def copy_tree(source,target):
    if not source.exists():return
    for p in source.rglob('*'):
        if not p.is_file() or p.is_symlink() or p.name=='.DS_Store':continue
        relative=p.relative_to(source).as_posix()
        if source.name=='config' and any(relative==v or relative.startswith(v+'/') for v in SKIP_CONFIG):continue
        if any(v in p.parts for v in ['__pycache__','.cache']):continue
        out=target/relative;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
def main():
    removal_policy=load_removal_policy(CLIENT.parent)
    client_jars=sorted((CLIENT/'mods').glob('*.jar'))
    client_rows=[{'file':jar.name,'modIds':sorted(jar_mod_ids(jar))} for jar in client_jars]
    retained_rows=[row for row in client_rows if not is_removed(row['file'],row['modIds'],removal_policy)]
    validate_mod_rows(retained_rows,removal_policy,client=True)
    mods=SERVER/'mods';mods.mkdir(exist_ok=True)
    if list(mods.glob('*.jar')):raise RuntimeError('Server mod directory is populated; inspect before rebuilding')
    mod_overlays=load_mod_overlays(ROOT)
    included=[];excluded=[];all_ids={'forge','minecraft','javafml','lowcodefml','mclanguage'}
    metadata_rows=[]
    for jar,policy_row in zip(client_jars,client_rows):
        rows=metadata(jar.read_bytes());ids=set(i for row in rows if not row['nested'] for i in row['ids'])
        entry={'file':jar.name,'sha256':sha(jar),'modIds':sorted(ids)}
        if is_removed(jar.name,policy_row['modIds'],removal_policy):
            excluded.append({**entry,'reason':'user-authorized persistent mod removal','exclusionType':'user-removal'});continue
        if ids&CLIENT_ONLY or jar.name.startswith('CrosshairBobbing'):
            excluded.append({**entry,'reason':'client interface/rendering/information component','exclusionType':'client-only'});continue
        target=mods/jar.name
        shutil.copy2(jar,target)
        if 'mutantmore' in ids:
            fix=patch_server_jar(target,ROOT/'evidence/mutantmore-server-fix')
            entry['upstreamSha256']=entry['sha256']
            entry['sha256']=fix['patchedJarSha256']
            entry['patch']='patch_mutantmore_server.py: MapDecorationTypeMixin moved to common mixins'
        apply_mod_overlay(target,entry,mod_overlays)
        included.append(entry)
        for row in rows:all_ids.update(row['ids']);metadata_rows.append((jar.name,row))
    for name, addition in load_server_additions(ROOT).items():
        if name in {row['file'] for row in included} or set(addition['modIds']) & all_ids:
            raise ValueError('Server-only addition conflicts with selected mods: ' + name)
        rows = metadata(addition['blob'])
        target = mods / name
        target.write_bytes(addition['blob'])
        included.append({'file': name, 'sha256': addition['sha256'], 'modIds': addition['modIds'],
            'patch': 'deployment/server-additions.json: ' + addition['patchId'], 'serverOnly': True})
        for row in rows:all_ids.update(row['ids']);metadata_rows.append((name,row))
    validate_mod_rows(included, removal_policy)
    missing=[]
    for jar,row in metadata_rows:
        dependencies=row['dependencies'] or {}
        if isinstance(dependencies,list):dependencies={','.join(row['ids']):dependencies}
        assert isinstance(dependencies,dict),(jar,dependencies)
        for owner,deps in dependencies.items():
            for dep in deps:
                if dep.get('mandatory') and dep.get('side','BOTH')!='CLIENT' and dep['modId'] not in all_ids:
                    missing.append({'file':jar,'owner':owner,'required':dep})
    dump(ROOT/'evidence/mod-selection.json',{'included':included,'excluded':excluded,'missingServerDependencies':missing,
        'removalPolicy':'clients/cmi-expedition/mod-removal-20261018.json',
        'removalPolicySha256':removal_policy['sha256'],'userRemovedModFiles':sorted(removal_policy['removedFiles'])})
    if missing:raise RuntimeError('Review server dependency list before launching')
    for folder in FOLDERS:copy_tree(CLIENT/folder,SERVER/folder)
    # Keep dedicated-server resource limits after copying shared client configs.
    copy_tree(ROOT/'deployment/config',SERVER/'config')
    for folder in ['startup_scripts','server_scripts','data','config','assets']:
        copy_tree(CLIENT/'kubejs'/folder,SERVER/'kubejs'/folder)
    for name in ['guide-tome-catalog.json','README.txt']:
        shutil.copy2(CLIENT/'kubejs'/name,SERVER/'kubejs'/name)
    # Dedicated-server generation overrides must survive shared client data copies.
    copy_tree(ROOT/'deployment/kubejs',SERVER/'kubejs')
    (SERVER/'eula.txt').write_text('eula=true\n')
    (SERVER/'user_jvm_args.txt').write_bytes((ROOT/'deployment/user_jvm_args.txt').read_bytes())
    # Loopback-only settings for the local dedicated-server validation run.
    (SERVER/'server.properties').write_text('server-ip=127.0.0.1\nserver-port=25575\nonline-mode=false\n'
        'level-name=expedition-local-validation\nmotd=Mechanical Expedition 0.2.0-test.1\n'
        'max-players=10\nview-distance=8\nsimulation-distance=5\nallow-flight=true\n'
        'difficulty=easy\npvp=false\nenable-command-block=true\nmax-tick-time=180000\n')
    dump(ROOT/'evidence/prepared.json',{'clientMods':len(included)+len(excluded),'serverMods':len(included),
        'excluded':len(excluded),'minecraft':'1.20.1','forge':'47.4.10','version':'0.2.0-test.1',
        'worldsIncluded':False,'sourceInstance':str(CLIENT),
        'userRemovalPolicyCount':len(removal_policy['removedFiles']),
        'excludedClientMods':sum(row['exclusionType']=='client-only' for row in excluded),
        'excludedUserModsPresentInSource':sum(row['exclusionType']=='user-removal' for row in excluded),
        'removalPolicySha256':removal_policy['sha256']})
    print(json.dumps({'serverMods':len(included),
        'excludedClientMods':sum(row['exclusionType']=='client-only' for row in excluded),
        'excludedUserModsPresentInSource':sum(row['exclusionType']=='user-removal' for row in excluded),
        'missingDependencies':len(missing)}))
if __name__=='__main__':main()
