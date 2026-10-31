"""Promote the reviewed v2 terrain assets, preserving the latest formal quest book."""
from pathlib import Path
import datetime, fcntl, hashlib, json, os, sys, tempfile

ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
CLIENT=ROOT/'clients/cmi-expedition'
SERVER=ROOT/'servers/cmi-expedition'
SOURCE=CLIENT/'tectonic-preview-v2/instance'
sys.path.insert(0,str(CLIENT/'tools'))
from mod_removal_policy import jar_mod_ids, load_removal_policy, validate_client_mods, validate_mod_rows

def sha(b):return hashlib.sha256(b).hexdigest()
def encoded(d):return (json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode()
def atomic(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=p.parent,prefix='.release-sync-',delete=False) as f:
        f.write(b); tmp=Path(f.name)
    os.replace(tmp,p)

def main():
    HERE.mkdir(parents=True,exist_ok=True)
    receipt=HERE/'terrain-promotion.json'
    if receipt.exists():raise SystemExit('Promotion already recorded; verify instead of overwriting')
    paths={r['path'] for r in json.loads((ROOT/'design/tectonic-preview-20261018/configuration/static-audit.json').read_text())['planned_files']}
    paths.update(r['path'] for r in json.loads((SOURCE/'.alpine-climate-installed.json').read_text())['files'])
    paths.update(json.loads((SOURCE/'.alpine-climate-extra-roots.json').read_text())['applied_files'])
    paths.update(str(p.relative_to(SOURCE)) for p in (SOURCE/'kubejs/data/cmi/lithostitched/worldgen_modifier/terrain_v2').glob('*.json'))
    assert len([p for p in paths if '/worldgen/placed_feature/' in p])==278
    blobs={p:(SOURCE/p).read_bytes() for p in sorted(paths)}
    assert sha(blobs['mods/expedition-alpine-climate-1.0.0.jar'])=='44b01c12f6b4be699b48c4d91f5f79227bdb4fb28cf698243a16d3eb4000b676'
    assert json.loads(blobs['config/tectonic.json'])['global_terrain']['max_y']==384
    stamp=datetime.datetime.now().astimezone().strftime('%Y%m%d-%H%M%S')
    backup=HERE/'backups'/stamp
    planned={}
    for rel,b in blobs.items():
        for base in [CLIENT/'instance',CLIENT/'overlay',SERVER/'instance']:
            planned[base/rel]=b
        if rel.startswith(('config/','kubejs/')):
            planned[SERVER/'deployment'/rel]=b
    policy_path=CLIENT/'mod-removal-20261018.json'
    policy=json.loads(policy_path.read_text())
    additions=policy.setdefault('approvedAdditions',[])
    approved={x['file'] for x in additions}
    for name in ['man_of_many_planes-0.2.1+1.20.1-forge.jar','expedition-alpine-climate-1.0.0.jar']:
        b=blobs.get('mods/'+name)
        if b is None:b=(CLIENT/'instance/mods'/name).read_bytes()
        if name not in approved:
            additions.append({'file': name, 'modIds': sorted(jar_mod_ids(b)), 'sha256': sha(b), 'approvalDate': '2026-10-18'})
        if name not in policy['expectedClientFiles']:policy['expectedClientFiles'].append(name)
    policy['expectedClientFiles'].sort()
    policy['expectedClientModCount']=len(policy['expectedClientFiles'])
    planned[policy_path]=encoded(policy)
    selection_path=SERVER/'evidence/mod-selection.json'
    selection=json.loads(selection_path.read_text())
    selected={x['file'] for x in selection['included']}
    for name in ['man_of_many_planes-0.2.1+1.20.1-forge.jar','expedition-alpine-climate-1.0.0.jar']:
        b=blobs.get('mods/'+name)
        if b is None:b=(SERVER/'instance/mods'/name).read_bytes()
        if name not in selected:selection['included'].append({'file':name,'sha256':sha(b),'modIds':sorted(jar_mod_ids(b))})
    selection['included'].sort(key=lambda x:x['file'])
    selection['removalPolicySha256']=sha(planned[policy_path])
    planned[selection_path]=encoded(selection)
    questroots=[CLIENT/'instance/config/ftbquests/quests',CLIENT/'overlay/config/ftbquests/quests',SERVER/'instance/config/ftbquests/quests']
    quest_before=[{str(p.relative_to(base)):sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()} for base in questroots]
    known_manifest=json.loads((CLIENT/'evidence/overlay-files.json').read_text())
    canonical_quests={}
    for rel in sorted(quest_before[0]):
        overlay=questroots[1]/rel
        source=overlay if overlay.exists() else questroots[0]/rel
        b=source.read_bytes()
        key='config/ftbquests/quests/'+rel
        if overlay.exists():assert sha(b)==known_manifest.get(key), 'Unreviewed overlay: '+rel
        canonical_quests[rel]=b
        for base in questroots:planned[base/rel]=b
    previous={p:p.read_bytes() if p.exists() else None for p in planned}
    manifest_path=CLIENT/'evidence/overlay-files.json'
    with (CLIENT/'evidence/.overlay-files.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        manifest=json.loads(manifest_path.read_text())
        previous[manifest_path]=manifest_path.read_bytes()
        for p,b in previous.items():
            if b is not None:
                dest=backup/p.relative_to(ROOT);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(b)
        for p,b in previous.items():assert (p.read_bytes() if p.exists() else None)==b, str(p)
        for p,b in planned.items():atomic(p,b)
        manifest.update({rel:sha(b) for rel,b in blobs.items()})
        manifest.update({'config/ftbquests/quests/'+rel:sha(b) for rel,b in canonical_quests.items()})
        atomic(manifest_path,encoded(manifest))
    policy=load_removal_policy(CLIENT)
    validate_client_mods(sorted((CLIENT/'instance/mods').glob('*.jar')),policy)
    validate_mod_rows(selection['included'],policy)
    for rel,b in blobs.items():
        for base in [CLIENT/'instance',CLIENT/'overlay',SERVER/'instance']:
            assert (base/rel).read_bytes()==b
    expected_quests={rel:sha(b) for rel,b in canonical_quests.items()}
    assert all({str(p.relative_to(base)):sha(p.read_bytes()) for p in base.rglob('*') if p.is_file()}==expected_quests for base in questroots)
    result={'at':datetime.datetime.now().astimezone().isoformat(),'terrain':'reviewed Tectonic v2 mountain coordination','files':[{'path':p,'sha256':sha(b),'bytes':len(b)} for p,b in blobs.items()], 'treeRoots':278,'structureFilters':10,'clientMods':policy['expectedClientModCount'],'serverMods':len(selection['included']),'latestQuestBookPreserved':True,'questChapters':len(list(questroots[0].glob('chapters/*.snbt'))),'backup':str(backup),'remoteDeploymentComplete':False,'worldsModified':False,'mapCachesModified':False}
    atomic(receipt,encoded(result))
    print(json.dumps({k:v for k,v in result.items() if k!='files'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
