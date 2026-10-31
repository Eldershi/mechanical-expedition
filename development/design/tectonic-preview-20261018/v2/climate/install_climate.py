"""Install only into the explicitly isolated v2 instance, before creating a save."""
from pathlib import Path
import argparse
import datetime as dt
import hashlib
import json
import os
import tempfile

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
EXPECTED=(PROJECT/'clients/cmi-expedition/tectonic-preview-v2/instance').resolve()

def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent,prefix='.alpine-',delete=False) as f:
        f.write(data);temp=Path(f.name)
    os.replace(temp,path)

def main():
    p=argparse.ArgumentParser();p.add_argument('--instance',type=Path,required=True);a=p.parse_args();instance=a.instance.resolve()
    if instance!=EXPECTED:p.error(f'Only the explicit v2 instance is allowed: {EXPECTED}')
    if list((instance/'saves').glob('*/level.dat')):p.error('Install climate before creating any save')
    marker=instance/'.alpine-climate-installed.json'
    if marker.exists():p.error('Alpine climate already installed')
    jar=HERE/'build/expedition-alpine-climate-1.0.0.jar'
    if not jar.exists():p.error('Run build_climate.py first')
    audit=json.loads((HERE.parents[1]/'configuration/static-audit.json').read_text())
    changes={'mods/'+jar.name:jar.read_bytes(),'config/expedition-alpine-climate.json':(HERE/'biome-policy.json').read_bytes()}
    for tree in audit['vegetation']['selected']:
        ns,_,name=tree['feature'].partition(':');rel=f'kubejs/data/{ns}/worldgen/placed_feature/{name}.json';path=instance/rel
        if not path.exists():p.error(f'Expected inherited v1 sparse-tree override: {rel}')
        obj=json.loads(path.read_text());modifier={'type':'expedition_alpine_climate:alpine_treeline'}
        if modifier in obj['placement']:p.error('Existing alpine tree filter without receipt')
        obj['placement'].append(modifier)
        changes[rel]=(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
    extras=list((HERE/'additional-placement-overrides').rglob('*.json'))
    for path in extras:
        rel='kubejs/data/'+path.relative_to(HERE/'additional-placement-overrides').as_posix()
        changes[rel]=path.read_bytes()
    backup=instance/'.alpine-climate-backups'/dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    manifest={'profile':'v2-local-alpine-bands','source_directory':str(HERE),'biome_source_replaced':False,'dimension_scope':'Actual surface-system and tree filters restricted to overworld; temperature hook restricted to listed overworld-only biome identities because Biome temperature API has no dimension parameter.','files':[]}
    for rel,data in changes.items():
        path=instance/rel
        if instance not in path.resolve().parents:p.error(f'Escaping target {rel}')
        old=path.read_bytes() if path.exists() else None
        if old is not None:write(backup/rel,old)
        manifest['files'].append({'path':rel,'before_sha256':hashlib.sha256(old).hexdigest() if old is not None else None,'after_sha256':hashlib.sha256(data).hexdigest()})
    for rel,data in changes.items():write(instance/rel,data)
    write(marker,(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'installed':str(jar),'target':str(instance),'tree_roots':len(audit['vegetation']['selected'])+len(extras),'receipt':str(marker),'launched':False},ensure_ascii=False))

if __name__=='__main__':main()
