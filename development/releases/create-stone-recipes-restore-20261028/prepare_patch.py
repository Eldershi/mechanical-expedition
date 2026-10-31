#!/usr/bin/env python3
"""Restore native Create mineral-stone processing without replacing CMI routes."""
import copy
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
RELEASE = Path(__file__).resolve().parent
REL = Path('kubejs/config/expedition-selected-native-recipes.json')
ACTIVE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
JAR = ACTIVE / 'mods/create-1.20.1-6.0.8.jar'
OLD_SHA = '57b0324c30ed349a4f2f4ae11afd9ff0d8b0f5e8253d468e4f2e92d6e6271b8d'
ROOTS = [Path('servers/cmi-expedition/deployment'), Path('servers/cmi-expedition/instance'), Path('clients/cmi-expedition/overlay')]
SELECTION = '机械动力石材原配方完整恢复（含矿石材、碎矿后处理及基础石材循环）'
PATHS = ([f'crushing/{stone}{suffix}' for stone in ('asurine','crimsite','ochrum','veridium') for suffix in ('','_recycling')]
         + [f'splashing/crushed_raw_{m}' for m in ('copper','gold','iron','zinc')]
         + [f'{mode}/{m}_ingot_from_crushed' for mode in ('smelting','blasting') for m in ('copper','gold','iron','zinc')]
         + [f'compacting/{s}_from_flint' for s in ('andesite','diorite','granite')]
         + ['mixing/lava_from_cobble'])

def sha(blob): return hashlib.sha256(blob).hexdigest()
def render(obj): return (json.dumps(obj, ensure_ascii=False, indent=2)+'\n').encode()

def inventory(create_rows, lang):
    prior = json.loads((PROJECT/'releases/netherite-recipe-restore-20261028/evidence/online-parallel-preflight.json').read_bytes())
    retained = set(prior['retainedIds'])
    old_rows = {r['nativeId']: r for r in prior['rows']}
    groups = {'newly_restored': [], 'previously_restored': [], 'already_retained': [], 'other_missing': [], 'condition_disabled': []}
    stone_items = {'minecraft:'+s for s in ('andesite','basalt','blackstone','calcite','cobblestone','cobbled_deepslate','deepslate','diorite','dripstone_block','end_stone','granite','gravel','magma_block','netherrack','obsidian','red_sand','red_sandstone','sand','sandstone','soul_sand','stone','tuff','nether_bricks','crying_obsidian','clay','terracotta','amethyst_block','amethyst_cluster','glowstone','gilded_blackstone','prismarine_crystals')}
    stone_items.update('create:'+s for s in ('asurine','crimsite','ochrum','veridium','limestone','scoria','scorchia'))
    types = {'create:crushing','create:milling','create:splashing','create:haunting','create:compacting','create:mixing'}
    extra = {'haunting/soul_sand','haunting/infested_stone_bricks','haunting/infested_mossy_stone_bricks','haunting/infested_cracked_stone_bricks','haunting/infested_chiseled_stone_bricks'}
    with zipfile.ZipFile(JAR) as archive:
        for name in archive.namelist():
            if not name.startswith('data/create/recipes/') or not name.endswith('.json') or '/compat/' in name: continue
            path = name.removeprefix('data/create/recipes/').removesuffix('.json')
            native = json.loads(archive.read(name))
            if path not in PATHS and path not in extra:
                if native.get('type') not in types: continue
                ins = native.get('ingredients', [])
                if not any(isinstance(i,dict) and (i.get('item') in stone_items or i.get('tag','').startswith('create:stone_types/') or i.get('tag')=='forge:cobblestone') for i in ins): continue
            rid = 'create:'+path
            row = {'nativeId':rid, 'sourceEntry':name, 'json':native}
            if path in PATHS:
                row['parallelId']='expedition:selected_native/create/'+path
                status='newly_restored'
            elif rid in old_rows and old_rows[rid]['status']!='native_condition_disabled':
                row['effectiveId']=old_rows[rid].get('id'); status='previously_restored'
            elif rid in retained: status='already_retained'
            elif rid in old_rows: status='condition_disabled'
            else: status='other_missing'
            groups[status].append(row)
    uf=[]
    uf_jar=ACTIVE/'mods/create_ultimate_factory-2.2.4-forge-1.20.1.jar'
    with zipfile.ZipFile(uf_jar) as archive:
        for name in archive.namelist():
            if not name.startswith('data/create_ultimate_factory/recipes/') or not name.endswith('.json'):continue
            native=json.loads(archive.read(name)); rid='create_ultimate_factory:'+name.removeprefix('data/create_ultimate_factory/recipes/').removesuffix('.json')
            uf.append({'nativeId':rid,'json':native,'retainedOnline':rid in retained,'sourceEntry':name})
    report={'observedBaselineAt':'2026-10-28 18:41:13 Asia/Shanghai','sourceCreateJar':str(JAR),'createVersion':'6.0.8','groups':groups,
            'ultimateFactoryVersion':'2.2.4','ultimateFactoryNativeRecipes':uf,
            'createStoneChineseNames':{s:lang.get('block.create.'+s) for s in ('asurine','crimsite','ochrum','veridium','limestone','scoria','scorchia')},
            'scope':'Create本体非矿石的石材/砂土/矿物加工及四种含矿石材的完整后处理；列出UF所有原生加工配方供核对；普通装饰切石、砖块、楼梯不属于资源处理恢复范围。'}
    assert not groups['other_missing'], 'Unaccounted native stone-processing recipes remain missing'
    report['counts']={k:len(v) for k,v in groups.items()}
    (RELEASE/'inventory.json').write_bytes(render(report))
    return report['counts']

def main():
    assert len(PATHS)==len(set(PATHS))==24
    rows=[]; source=[]
    with zipfile.ZipFile(JAR) as archive:
        lang=json.loads(archive.read('assets/create/lang/zh_cn.json'))
        for path in PATHS:
            entry='data/create/recipes/'+path+'.json'; blob=archive.read(entry); native=json.loads(blob)
            outputs=[r['item'] for r in native.get('results',[]) if 'item' in r]
            if isinstance(native.get('result'),str):outputs.append(native['result'])
            rows.append({'nativeId':'create:'+path,'json':native,'outputs':outputs,'source':JAR.name,'sourceEntry':entry,'sourceJsonSha256':sha(blob),'id':'expedition:selected_native/create/'+path,'selections':[SELECTION]})
            source.append((entry,blob))
    by_path={r['nativeId'].removeprefix('create:'):r for r in rows}
    for stone,metal in {'asurine':'zinc','crimsite':'iron','ochrum':'gold','veridium':'copper'}.items():
        item='create:crushed_raw_'+metal
        for suffix in ('','_recycling'):assert item in by_path['crushing/'+stone+suffix]['outputs']
        assert by_path['splashing/crushed_raw_'+metal]['json']['ingredients']==[{'item':item}]
        for mode in ('smelting','blasting'):assert by_path[f'{mode}/{metal}_ingot_from_crushed']['json']['ingredient']=={'item':item}
    prepared=[]
    for root in ROOTS:
        target=PROJECT/root/REL; backup=RELEASE/'backups/project-before'/root/REL
        original=backup.read_bytes() if backup.exists() else target.read_bytes()
        assert sha(original)==OLD_SHA, f'Unexpected baseline: {target}'
        baseline=json.loads(original); assert len(baseline['recipes'])==2473 and baseline['selectionCount']==240
        assert not ({r['nativeId'] for r in rows}&{r['nativeId'] for r in baseline['recipes']})
        assert not ({r['id'] for r in rows}&{r['id'] for r in baseline['recipes']})
        updated=copy.deepcopy(baseline);updated['selectionCount']=241;updated['recipes'].extend(rows);new=render(updated)
        assert len(updated['recipes'])==2497
        restored=copy.deepcopy(updated);restored['selectionCount']=240;del restored['recipes'][-24:];assert restored==baseline
        assert target.read_bytes() in (original,new),f'Target changed: {target}'
        prepared.append((target,backup,original,new))
    # Inventory completeness is a readiness gate, before any source catalog changes.
    RELEASE.mkdir(parents=True,exist_ok=True)
    counts=inventory(rows,lang)
    for target,backup,original,new in prepared:
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_bytes(original)
        target.write_bytes(new);assert target.read_bytes()==new
    payload=RELEASE/'payload'/REL;payload.parent.mkdir(parents=True,exist_ok=True);payload.write_bytes(prepared[0][3])
    for entry,blob in source:
        p=RELEASE/'evidence/native-json'/entry;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(blob)
    installer=(PROJECT/'releases/netherite-recipe-restore-20261028/install_active_client.py').read_text().replace('.netherite-recipe-restore-','.create-stone-recipe-restore-')
    (RELEASE/'install_active_client.py').write_text(installer)
    before=PROJECT/'releases/netherite-recipe-restore-20261028/evidence/online-catalog-readback.json';assert sha(before.read_bytes())==OLD_SHA
    backup=RELEASE/'backups/server-before'/REL;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(before,backup)
    manifest={'createdAtUtc':datetime.now(timezone.utc).isoformat(),'operation':'parallel_restore_create_mineral_stone_processing','sourceJar':str(JAR),'sourceJarSha256':sha(JAR.read_bytes()),'oldCatalogSha256':OLD_SHA,'newCatalogSha256':sha(prepared[0][3]),'selectionCountBefore':240,'selectionCountAfter':241,'recipeCountBefore':2473,'recipeCountAfter':2497,'addedRecipeCount':24,'addedNativeIds':[r['nativeId'] for r in rows],'addedRecipeIds':[r['id'] for r in rows],'inventoryCounts':counts,
              'verification':{'nativeJsonUnmodified':True,'allExistingRecipeRowsUnchanged':True,'allOtherCatalogFieldsUnchanged':True,'addedExactly24Recipes':True,'fourMineralStoneProcessingChainsComplete':True,'allRelatedNativeProcessingAccountedFor':True,'workspaceTargetsIdentical':True},
              'workspaceTargets':[{'path':str(t),'backup':str(b),'beforeSha256':sha(o),'afterSha256':sha(n)} for t,b,o,n in prepared],
              'payload':str(payload),'activeClientInstall':{'status':'pending','destination':str(ACTIVE/REL),'observedDestinationSha256':sha((ACTIVE/REL).read_bytes())},'onlineDeployment':{'status':'pending'}}
    (RELEASE/'manifest.json').write_bytes(render(manifest))
    print(json.dumps({'newCatalogSha256':manifest['newCatalogSha256'],'inventoryCounts':counts,'added':24,'activeClientModified':False},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
