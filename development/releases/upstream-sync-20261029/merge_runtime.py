#!/usr/bin/env python3
"""Merge runtime-owned paths into a disposable staging tree; never deploy."""
from pathlib import Path
import copy, hashlib, importlib.util, json, re, shutil, subprocess, tempfile

ROOT=Path(__file__).resolve().parent
STAGE=ROOT/'staging'; UP=ROOT/'upstream'; PROJECT=ROOT.parent.parent
OWNED=('kubejs/startup_scripts/','kubejs/server_scripts/tags/','ldlib/','hotai/','config/nebula/')
manifest={'adopted':[],'keptLegacy':[],'compatibility':[],'shapeExceptions':[]}
inventory=json.loads((PROJECT/'evidence/upstream-review-20261029/file-inventory.json').read_text())
spec=importlib.util.spec_from_file_location('nbttool',UP/'Developer/MBD2-NBT工具/_nbt_tool.py')
nbt=importlib.util.module_from_spec(spec); spec.loader.exec_module(nbt)
def get(comp,key): return next((v for k,v in comp if k==key),None)
def put(comp,key,val):
    for i,(k,v) in enumerate(comp):
        if k==key: comp[i]=(key,val); return
    comp.append((key,val))
def read_nbt(path):
    name,root,trailing,data=nbt.read_file(path)
    if trailing: raise ValueError('NBT trailing bytes: '+str(path))
    return name,root
def write_nbt(path,name,root):
    w=nbt.Writer(); w.u1(10); w.string(name); nbt.write_payload(w,10,root)
    path.write_bytes(bytes(w.buf))
def primitive(v):
    if isinstance(v,nbt.Tag): return primitive(v.value)
    if isinstance(v,nbt.Compound): return {k:primitive(v) for k,v in v}
    if isinstance(v,nbt.List): return [primitive(x) for x in v]
    return v
def blob(raw): return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

for row in inventory:
    rel=row['path']
    if not rel.startswith(OWNED): continue
    src,dst=UP/rel,STAGE/rel
    if row['status']=='removed':
        manifest['keptLegacy'].append({'path':rel,'reason':'retain registered legacy machine/steam identity'})
        continue
    if rel=='kubejs/startup_scripts/register/block/Casing.js':
        manifest['keptLegacy'].append({'path':rel,'reason':'keep existing cmi:bronze_casing registered'})
        continue
    if rel.endswith('.mb') and dst.exists():
        _,old=read_nbt(dst); new_name,new=read_nbt(src)
        old_h=get(old,'placeholders'); new_h=get(new,'placeholders')
        old_pred=get(get(old,'resources').value,'mbd2.gui.editor.group.predicate')
        new_pred=get(get(new,'resources').value,'mbd2.gui.editor.group.predicate')
        for key,old_tag in old_pred.value:
            new_tag=get(new_pred.value,key)
            if new_tag is None:
                new_pred.value.append((key,copy.deepcopy(old_tag))); continue
            old_blocks=get(old_tag.value,'blocks'); new_blocks=get(new_tag.value,'blocks')
            if old_blocks and new_blocks:
                have={json.dumps(primitive(x),sort_keys=True) for x in new_blocks.value.items}
                for block in old_blocks.value.items:
                    if json.dumps(primitive(block),sort_keys=True) not in have:
                        new_blocks.value.items.append(copy.deepcopy(block))
        if primitive(old_h)!=primitive(new_h):
            for key in ('placeholders','shape_infos','aisle_repetitions','layer_axis'):
                val=get(old,key)
                if val is not None: put(new,key,copy.deepcopy(val))
            manifest['shapeExceptions'].append({'path':rel,'reason':'preserve legacy controller shape; adopt upstream logic/UI/ports'})
        dst.parent.mkdir(parents=True,exist_ok=True); write_nbt(dst,new_name,new)
        manifest['adopted'].append(rel); continue
    dst.parent.mkdir(parents=True,exist_ok=True)
    if rel.endswith('.js') and dst.exists() and blob(dst.read_bytes())!=(row.get('base') or {}).get('sha'):
        baseline=ROOT/'base'/rel
        if not baseline.exists(): raise RuntimeError('Need exact base for diverged file: '+rel)
        current=dst.read_text().replace('\r\n','\n'); head=src.read_text().replace('\r\n','\n')
        with tempfile.TemporaryDirectory(dir=ROOT) as td:
            paths=[Path(td)/x for x in ['ours','base','theirs']]
            for p,s in zip(paths,[current,baseline.read_text().replace('\r\n','\n'),head]): p.write_text(s)
            merge=subprocess.run(['git','merge-file','-p',*map(str,paths)],capture_output=True,text=True)
            merged=merge.stdout
            if merge.returncode and rel=='kubejs/server_scripts/tags/Block.js':
                conflict=r'<<<<<<<[^\n]*\n(.*?)=======\n(.*?)>>>>>>>[^\n]*\n'
                def keep_both(m):
                    if '"@rechiseledcreate"' not in m[1] or '"@pipez"' not in m[2]:
                        raise RuntimeError('Unexpected block tag conflict')
                    return m[1]+m[2]
                merged=re.sub(conflict,keep_both,merged,flags=re.S)
            if '<<<<<<<' in merged or merge.returncode>1: raise RuntimeError('Manual merge needed: '+rel)
            dst.write_text(merged)
    else: shutil.copy2(src,dst)
    manifest['adopted'].append(rel)

p=STAGE/'kubejs/server_scripts/tags/Item.js'
s=p.read_text().replace('\n\tevent.get("forge:plates/andesite_alloy")\n\t\t.add("#forge:plates/andesite")','')
p.write_text(s)
manifest['compatibility'].append('keep one-way andesite plate alias; avoid mutual tag dependency')

# Existing cmi solar boilers keep their old throughput.
p=STAGE/'kubejs/startup_scripts/register/block/SteamEngine.js'
s=p.read_text().replace('.production(24)','.production(38)').replace('.production(48)','.production(75)')
p.write_text(s)
legacy='''// Expedition: retain saved materials and machine registry identities.
StartupEvents.registry("mekanism:gas", event => {
  event.create("cmi:nuke_waste").color(0x4F412A)
  event.create("cmi:spent_nuke_waste").color(0x262015)
})
StartupEvents.registry("item", event => {
  event.create("cmi:basalt_general_component")
    .texture("cmi:item/material/general_component/basalz")
    .tag("cmi:general_components")
})
StartupEvents.registry("block", event => {
  event.create("cmi:bronze_solar_boiler", "steam_letters:solar")
    .material("steam_letters:bronze").production(19).capacity(4000)
  event.create("cmi:bronze_fluid_burner", "steam_letters:fluid_burner")
    .material("steam_letters:bronze")
})
'''
p=STAGE/'kubejs/startup_scripts/expedition/UpstreamLegacyRegistrations.js'
p.parent.mkdir(parents=True,exist_ok=True); p.write_text(legacy)
manifest['compatibility'] += ['retain cmi:nuke_waste and cmi:spent_nuke_waste gases','retain cmi:basalt_general_component item','retain cmi bronze solar boiler/fluid burner using new implementation','existing solar boiler throughput retained at 19/38/75']
out=ROOT/'evidence/scope-manifest-runtime-merge.json'
out.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'adopted':len(manifest['adopted']),'keptLegacy':len(manifest['keptLegacy']),'shapeExceptions':manifest['shapeExceptions']},ensure_ascii=False,indent=2))
