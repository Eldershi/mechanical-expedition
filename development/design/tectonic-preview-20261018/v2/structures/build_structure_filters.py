#!/usr/bin/env python3
"""Build a reviewed finite whitelist of Lithostitched 1.4.11 spawn conditions.

This writes only v2 design artifacts. It never edits an instance or a save.
"""
from pathlib import Path
from zipfile import ZipFile
import collections, hashlib, json, re

HERE=Path(__file__).resolve().parent
PREVIEW=HERE.parents[1]
WORKSPACE=HERE.parents[3]
MODS=WORKSPACE/'clients/cmi-expedition/tectonic-preview/instance/mods'
INVENTORY=PREVIEW/'assessment/structure-config-inventory.json'


def rid(path):
    return re.sub(r'^data/([^/]+)/worldgen/structure/(.*)\.json$',r'\1:\2',path)


def grid(radius,step,limit):
    n=(radius*2//step+1)**2
    return {'type':'lithostitched:grid','radius':radius,'distance_between_points':step,
            'condition':{'type':'lithostitched:height_filter','range_type':'heightmap_relative',
                         'heightmap':'OCEAN_FLOOR_WG','permitted_range':{'min_inclusive':-limit,'max_inclusive':limit}},
            'allowed_count':{'min_inclusive':n,'max_inclusive':n}}


def main():
    raw=json.loads(INVENTORY.read_text());resources={};provenance={}
    for jar,entry in raw.items():
        for path,value in entry['structures'].items():
            resources[rid(path)]=value;provenance[rid(path)]={'jar':jar,'resource':path}
    # Include the actual installed windmill family; template format and one saved 17×14 footprint were checked.
    with ZipFile(MODS/'cso-2.0.0-forge.jar') as z:
        for path in z.namelist():
            if re.match(r'^data/cso/worldgen/structure/[^/]+\.json$',path):
                resources[rid(path)]=json.loads(z.read(path));provenance[rid(path)]={'jar':'cso-2.0.0-forge.jar','resource':path}
    vanilla=['minecraft:village_'+b for b in ['plains','desert','savanna','snowy','taiga']]
    client=(Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/versions/1.20.1/1.20.1.jar')
    with ZipFile(client) as z:
        for ident in vanilla:
            if ident in resources:continue
            path='data/minecraft/worldgen/structure/'+ident.split(':')[1]+'.json'
            resources[ident]=json.loads(z.read(path));provenance[ident]={'jar':str(client),'resource':path}
    groups={};claims={}
    def add(name,ids,conditions,rationale):
        ids=sorted(set(ids))
        if not ids:raise ValueError('Empty whitelist '+name)
        by_offset=collections.defaultdict(list)
        for ident in ids:
            if ident not in resources:raise ValueError('Missing installed structure '+ident)
            if ident in claims:raise ValueError('Duplicate filter '+ident)
            data=resources[ident]
            if data.get('step') not in ['surface_structures','raw_generation']:
                raise ValueError('Unexpected underground/non-surface step '+ident)
            if data.get('project_start_to_heightmap') not in ['WORLD_SURFACE_WG','OCEAN_FLOOR_WG']:
                raise ValueError('Not an ordinary projected land structure '+ident)
            start=data.get('start_height',{})
            if set(start)!= {'absolute'} or not isinstance(start['absolute'],int) or data.get('start_jigsaw_name'):
                raise ValueError('Nontrivial/variable anchor needs individual review '+ident)
            by_offset[start['absolute']].append(ident)
        for offset,subset in sorted(by_offset.items()):
            variant=name if offset==0 else name+('_anchor_plus' if offset>0 else '_anchor_minus')+str(abs(offset))
            shifted=json.loads(json.dumps(conditions))
            for cond in shifted:
                permitted=cond['condition']['permitted_range']
                permitted['min_inclusive']+=offset;permitted['max_inclusive']+=offset
            for ident in subset:claims[ident]=variant
            groups[variant]={'ids':subset,'conditions':shifted,'rationale':rationale,'authoredAnchorOffsetY':offset}

    # Explicit ordinary mainland variants. Excluded: beach/oasis/tree villages, mountain/alpine, swamp and underground.
    ctov_variants=['christmas','dark_forest','desert','jungle','mesa','mesa_fortified','mushroom',
                   'plains','plains_fortified','savanna','savanna_na','snowy_igloo','taiga','taiga_fortified']
    add('villages_small',['ctov:small/village_'+v for v in ctov_variants],
        [grid(64,64,28),grid(24,12,8)],'Small village: strict 48×48 core, loose 128×128 outer guard; roads retain gradual height changes.')
    add('villages_large',['ctov:large/village_'+v for v in ctov_variants],
        [grid(80,80,36),grid(40,20,12)],'Large village: 80×80 core, loose 160×160 guard; no demand that the entire village be flat.')
    town_villages=['exclusives/village_'+v for v in ['classic','iberian','mediterranean','rustic','swedish','tudor']]
    town_villages+=['village_'+v for v in ['badlands','birch_forest','flower_forest','forest','jungle','meadow',
                                         'mushroom_fields','old_growth_taiga','savanna_plateau','snowy_taiga',
                                         'sparse_jungle','sunflower_plains','wooded_badlands']]
    ordinary=vanilla+['ctov:medium/village_'+v for v in ctov_variants]+['towns_and_towers:'+v for v in town_villages]
    add('villages_standard',ordinary,[grid(80,80,32),grid(32,16,10)],
        'Ordinary land villages: loose 160×160 outer relief guard plus strict 64×64 starting core. Specialist shore/tree/mountain villages excluded.')
    windmills=[ident for ident in resources if ident.startswith('cso:') and ident.endswith('windmill')]
    add('windmills',windmills,[grid(16,8,6)],
        'Rigid compact windmills: 32×32 footprint guard includes the observed 17×14 placed base and a margin; max 25 height samples.')
    taverns=['nova_structures:tavern_'+v for v in ['acacia','birch','cherry','dark_oak','desert','jungle','oak','snowy','spruce']]
    add('taverns',taverns,[grid(32,16,10)],
        'Mainland taverns: 64×64 guard covers the observed 40×21 connected tavern footprint. Wetland/stilt variants excluded.')
    add('land_houses',['structory:old_manor','structory:outcast_villager_grassy','structory:outcast_villager_desert',
                       'structory:abandoned_chapel','dungeons_arise:greenwood_pub','dungeons_arise:small_prairie_house'],
        [grid(48,48,22),grid(24,12,8)],'Selected ordinary land houses/manors: preserve modest surrounding slopes, screen sharp relief near the main base.')
    add('large_land_buildings',['dungeons_arise:bathhouse','dungeons_arise:illager_fort','dungeons_arise:monastery',
                               'dungeons_arise:shiraz_palace','nova_structures:illager_manor'],
        [grid(114,114,36),grid(48,24,14)],'Selected large ground buildings: permissive 228×228 outer guard and 96×96 main-foundation core; airships/mines/treehouses excluded.')
    destination=HERE/'datapack';data_dir=destination/'data/cmi/lithostitched/worldgen_modifier/terrain_v2'
    data_dir.mkdir(parents=True,exist_ok=True)
    (destination/'pack.mcmeta').write_text(json.dumps({'pack':{'pack_format':15,'description':'Expedition Tectonic v2: selected mainland structure terrain guards'}},ensure_ascii=False,indent=2)+'\n')
    manifest=[]
    for name,group in groups.items():
        conditions=group['conditions']
        resource={'type':'lithostitched:set_structure_spawn_condition','structures':group['ids'],'append':True,
                  'spawn_condition':conditions[0] if len(conditions)==1 else conditions}
        path=data_dir/(name+'.json');path.write_text(json.dumps(resource,ensure_ascii=False,indent=2)+'\n')
        for ident in group['ids']:
            definition=resources[ident]
            manifest.append({'id':ident,'group':name,'definition':provenance[ident],
                             'originalType':definition.get('type'),'terrainAdaptation':definition.get('terrain_adaptation','default none'),
                             'startHeight':definition.get('start_height'),'projectStartToHeightmap':definition.get('project_start_to_heightmap'),
                             'maxDistanceFromCenter':definition.get('max_distance_from_center'),
                             'startPool':definition.get('start_pool')})
        group['resource']=str(path.relative_to(destination))
        group['maxHeightQueriesPerCandidate']=sum(c['allowed_count']['max_inclusive'] for c in conditions)
    excluded={
        'IDAS and MoogsVoyager/MoogsStructureLib':'Existing custom terrain/burying/biome checks preserved; not wrapped in this pass.',
        'Repurposed Structures':'Ocean villages, underground variants and custom mansion foundations not reinterpreted by a generic land filter.',
        'specialist CTOV':'beach/desert_oasis/jungle_tree/mountain/mountain_alpine/swamp/swamp_fortified/underground',
        'specialist Towns and Towers':'ocean/beach/swamp/grove/snowy_slopes and exclusive nilotic/piglin/trader-camp; all pillager outposts unchanged.',
        'other dimensions and intentionally floating':'nether/end structures, skyships, floating islands and tree houses unchanged.',
        'underground or aquatic structures':'All non-selected mines, crypts, ruins, shipwrecks, ocean structures and mountain-specific structures unchanged.'}
    files={str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(destination.rglob('*.json'))}
    metadata={'lithostitchedVersion':'1.4.11','builtFromInstalledResourcesOnly':True,'selectedStructures':len(manifest),
              'groupCounts':dict(collections.Counter(x['group'] for x in manifest)),
              'heightmap':'OCEAN_FLOOR_WG','comparison':'generation stub Y minus native first-occupied ground height at each grid point',
              'conditionsAreSamplingNotExhaustiveFootprint':True,'appendExistingSpawnConditions':True,
              'retentionRateMeasured':False,'runtimeCodecValidationPending':True,
              'groups':groups,'structures':manifest,'explicitExclusions':excluded,'resourceSha256':files}
    (HERE/'structure-filter-manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    # Static validation against exact installed class registration strings and field names.
    code=(PREVIEW/'assessment/decompiled/dev/worldgen/lithostitched/LithostitchedCommon.java').read_text()
    for name in ['set_structure_spawn_condition','grid','height_filter']:
        if '"'+name+'"' not in code:raise ValueError('Unregistered codec type '+name)
    for path in destination.rglob('*.json'):json.loads(path.read_text())
    print(json.dumps({'structures':len(manifest),'groups':metadata['groupCounts'],'datapack':str(destination.resolve()),'resourceFiles':len(files),
                      'jsonAndInstalledRegistryTypeValidation':'passed','runtimeCodecValidation':'pending v2 boot'},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
