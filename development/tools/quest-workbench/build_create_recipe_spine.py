#!/usr/bin/env python3
"""Generate the recipe-backed Create introduction; write draft files only."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
OUTPUT=ROOT/'design/create-recipe-spine-draft'
BASELINE=ROOT/'design/create-progression-draft/source-inventory.json'
AUDIT=ROOT/'tools/quest-workbench/evidence/create-recipe-spine-audit.json'
LIVE=ROOT/'clients/cmi-expedition/instance/config/ftbquests/quests/chapters'
SEED='cmi-expedition/create-recipe-spine/1.20.1/v1/'
MAIN_GROUP='050255AE19A93344'
TOPIC_GROUP={'id':'6977257A15C2F0DE','title':'机械动力专题'}
MAIN='create_basics_orientation.snbt'
FILES=[MAIN,'create_basics_create_logistics.snbt','create_basics_structures.snbt','create_basics_create_trains.snbt']
SOURCE_CURRENT='design/create-recipe-spine-draft/source/current-chapters'
RAW_ITEMS=['minecraft:andesite','minecraft:iron_nugget','minecraft:iron_block','minecraft:iron_ingot',
           'minecraft:gold_ingot','minecraft:copper_ingot']
NAMES={'minecraft:andesite':'安山岩','minecraft:iron_nugget':'铁粒','minecraft:iron_block':'铁块',
       'minecraft:iron_ingot':'铁锭','minecraft:gold_ingot':'金锭','minecraft:copper_ingot':'铜锭',
       'minecraft:stick':'木棍','minecraft:string':'线','minecraft:glass':'玻璃','minecraft:stone':'石头',
       'minecraft:oak_planks':'木板','minecraft:oak_slab':'木台阶','minecraft:barrel':'木桶',
       'minecraft:iron_bars':'铁栏杆','minecraft:paper':'纸','minecraft:sand':'沙子',
       'minecraft:redstone':'红石粉','minecraft:compass':'指南针','minecraft:dried_kelp':'海带干',
       'minecraft:white_wool':'羊毛','create:cogwheel':'小齿轮','create:whisk':'搅拌头'}
NEW_ITEMS=['minecraft:andesite','minecraft:iron_nugget','create:andesite_alloy','#forge:stripped_logs',
           'minecraft:iron_block','minecraft:iron_ingot','minecraft:gold_ingot','minecraft:copper_ingot',
           'thermal:iron_plate','thermal:gold_plate','thermal:copper_plate','create:whisk','create:propeller']
OPTIONAL_CORE={'create:hand_crank','create:water_wheel','create:large_water_wheel','create:windmill_bearing','create:sail_frame','create:white_sail',
               'create:gearbox','create:clutch','create:gearshift','create:sand_paper',
               'create:speedometer','create:stressometer','create:mechanical_drill','create:item_drain'}
LATE={'create:crushing_wheel','create:deployer','create:mechanical_crafter','create:rotation_speed_controller','create:steam_engine'}
OLD_IDS={'precision':'1570B04A1D692BCC','railway':'6BA8D6727D497F84','steam_component':'5BB078BA5116FE68',
         'steam_station':'12CEF39F02D4EB3A','electron_tube':'095B15FB9AA8B9AB','brass':'2F00DD29F68238BA'}
RECIPE_OVERRIDES={
 'create:large_cogwheel':'expedition:pre_steam/native/create/crafting/kinetics/large_cogwheel',
 'create:sail_frame':'create:crafting/kinetics/sail_framefrom_conversion',
 'create:white_sail':'expedition:pre_steam/native/create/crafting/kinetics/white_sail_from_conversion',
 'create:copper_casing':'expedition:pre_steam/native/create/item_application/copper_casing_from_log',
}

CORE_LAYOUT = {'create:andesite_casing': [9.0, 1.0],
 'create:shaft': [9.0, -1.0],
 'create:cogwheel': [13.75, -10.05],
 'create:large_cogwheel': [13.75, -13.7],
 'create:hand_crank': [9.5, -7.6],
 'create:water_wheel': [13.0, -15.25],
 'create:large_water_wheel': [17.5, -15.75],
 'create:windmill_bearing': [13.0, -0.6],
 'create:white_sail': [12.5, 13.5],
 'create:gearbox': [18.5, -11.55],
 'create:clutch': [14.25, -4.05],
 'create:gearshift': [17.5, -0.75],
 'create:depot': [12.75, 8.1],
 'create:mechanical_press': [13.5, 1.0],
 'create:millstone': [18.75, -14.1],
 'create:encased_fan': [27.5, -12.55],
 'create:copper_casing': [18.25, -8.1],
 'create:fluid_pipe': [22.5, 12.1],
 'create:mechanical_pump': [27.75, 3.45],
 'create:fluid_tank': [22.25, 10.1],
 'create:basin': [8.0, 7.25],
 'create:mechanical_mixer': [27.0, 1.0],
 'create:spout': [23.0, -14.55],
 'create:item_drain': [23.0, -3.75],
 'create:sand_paper': [14.25, -2.1],
 'create:wrench': [22.5, 5.0],
 'create:goggles': [22.5, 7.0],
 'create:speedometer': [12.5, 2.55],
 'create:stressometer': [18.25, 6.4],
 'create:mechanical_drill': [18.25, 13.3],
 'create:sail_frame': [9.5, 15.6],
 'minecraft:andesite': [0.0, 0.0],
 'minecraft:iron_nugget': [0.0, 2.0],
 'create:andesite_alloy': [4.5, 1.0],
 '#forge:stripped_logs': [5.0, -3.0],
 'minecraft:iron_block': [8.25, 3.1],
 'minecraft:iron_ingot': [15.0, -1.0],
 'minecraft:gold_ingot': [15.5, 6.75],
 'minecraft:copper_ingot': [13.0, 11.95],
 'thermal:iron_plate': [18.0, 1.0],
 'thermal:gold_plate': [18.0, 5.0],
 'thermal:copper_plate': [19.0, 10.6],
 'create:whisk': [22.5, 1.0],
 'create:propeller': [23.5, -7.3]}

def ident(kind,key):
    return f'{int(hashlib.sha256((SEED+kind+"/"+key).encode()).hexdigest()[:16],16)&0x7fffffffffffffff:016X}'

def sha(blob):return hashlib.sha256(blob).hexdigest()

def snbt(value,depth=0):
    tab='\t'*depth;child='\t'*(depth+1)
    if isinstance(value,str):return json.dumps(value,ensure_ascii=False)
    if isinstance(value,bool):return 'true' if value else 'false'
    if isinstance(value,int):return str(value)
    if isinstance(value,float):return repr(value)+'d'
    if isinstance(value,list):
        if not value:return '[ ]'
        if len(value)<4 and all(isinstance(x,(str,int,bool)) for x in value):return '['+' '.join(snbt(x,depth) for x in value)+']'
        return '[\n'+'\n'.join(child+snbt(x,depth+1) for x in value)+'\n'+tab+']'
    if isinstance(value,dict):
        if not value:return '{ }'
        return '{\n'+'\n'.join(child+(k if re.fullmatch(r'[\w.+-]+',k) else snbt(k))+': '+snbt(v,depth+1) for k,v in value.items())+'\n'+tab+'}'
    raise TypeError(type(value))

def parser():
    spec=importlib.util.spec_from_file_location('spine_snbt',ROOT/'clients/cmi-expedition/tools/ftb_snbt.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.loads

def freeze(output,loads,check):
    baseline_blob=BASELINE.read_bytes()
    saved=output/'source/tutorial-baseline.json'
    if not saved.exists():
        if check:raise ValueError('Frozen tutorial baseline missing')
        saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(baseline_blob)
    if saved.read_bytes()!=baseline_blob:raise ValueError('Frozen original tutorial baseline changed')
    current={};hashes={}
    for name in FILES:
        file=output/'source/current-chapters'/name
        if not file.exists():
            if check:raise ValueError('Frozen current four-chapter baseline missing')
            file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes((LIVE/name).read_bytes())
        blob=file.read_bytes();current[name]=loads(blob.decode());hashes[name]=sha(blob)
    return json.loads(baseline_blob),current,{'path':BASELINE.relative_to(ROOT).as_posix(),'sha256':sha(baseline_blob),
        'sourceCurrentDirectory':SOURCE_CURRENT,'sourceCurrentChapterHashes':hashes}

def catalog():
    active=json.loads((ROOT/'tools/quest-workbench/data/active-export.json').read_text())
    path=Path(active['exportRoot'])/'items.json'
    return {item['id']:item for item in json.loads(path.read_text())['items']}

def selected(item,audit):
    entry=audit['items'][item]
    recipe_id=RECIPE_OVERRIDES.get(item,entry['selectedRecipeId'])
    route=next((r for r in entry['recipeRoutes'] if r['id']==recipe_id),None)
    if not route:raise ValueError('Selected audited recipe missing: '+recipe_id)
    return route

def material_name(options):
    ids={option['id'] for option in options}
    if 'minecraft:stripped_oak_log' in ids and len(ids)>20:return '任意去皮原木'
    if 'minecraft:stripped_oak_wood' in ids and len(ids)>20:return '任意去皮木'
    preference=['create:cogwheel','minecraft:stick','minecraft:string','minecraft:oak_planks',
                'minecraft:oak_slab','minecraft:glass','minecraft:stone','minecraft:white_wool']
    chosen=next((option for key in preference for option in options if option['id']==key),options[0])
    name=NAMES.get(chosen['id'],chosen.get('name',chosen['id']))
    return chosen['id'] if 'translation{' in name else name

def inputs_text(route):
    parts=[];groups={}
    for slot in route['inputs']:
        options=slot.get('options',[])
        if not options:continue
        first=options[0]
        label=material_name(options)
        count=first.get('count',1)
        signature=tuple(sorted(option['id'] for option in options))
        if signature not in groups:groups[signature]=[label,0]
        groups[signature][1]+=count
    for label,count in groups.values():parts.append(f'{label}×{count}')
    return '、'.join(parts)

def recipe_description(item,audit,route):
    entry=audit['items'][item]
    machines=route.get('machines') or ([route['machine']] if route.get('machine') else [])
    machine_names=[audit['items'].get(machine,{}).get('name',machine) for machine in machines]
    method='使用'+('、'.join(machine_names)) if machines else '按当前合成/应用配方制作'
    if route['type']=='create:item_application':method='把材料应用在放置的去皮原木上'
    output='、'.join(material_name(slot['options'])+'×'+str(slot['options'][0].get('count',1)) for slot in route['outputs'] if slot.get('options'))
    paragraphs=[f'配方起步：{method}。所需材料：{inputs_text(route)} → {output}。点击物品查看当前配方与替代材料。',
                '']
    if item in OPTIONAL_CORE:paragraphs.append('可选分支：按当前工位需求选择，不要求把全部动力形式或辅助工具都做一遍。')
    if item in {'thermal:iron_plate','thermal:gold_plate','thermal:copper_plate'}:
        paragraphs.append('可用动力冲压机批量压板，也可按配方选择矿锤等加工方式。铁、金、铜板材可分别准备。')
    if item in {'create:wrench','create:goggles'}:
        paragraphs.append('本包这件工具使用金板，不是铁板。先建立冲压能力，再从金板分支制作；铁板会用于搅拌头和扇叶等后续工艺。')
    if item=='create:mechanical_press':
        paragraphs.append('接轴供能，在冲压机下方正确放置置物台或工作盆，投入有效原料，检查加工空间、应力与成品收集；手摇、水力和风力可按需要选用。')
    if item=='create:sail_frame':paragraphs.append('用线和木棍制作风帆框架，也可按配方在框架与风帆之间转换；空框架本身不能提供风力。')
    return paragraphs

def filter_stack(audit):
    group=audit['tagInputGroups']['forge:stripped_logs']
    options=group['resolvedOptions']
    ids=sorted({o['id'] for o in options})
    return copy.deepcopy(group['taskFilterStack']),ids

def task(qid,tid,item,title,count=1):
    return {'id':tid,'type':'item','title':'获得'+title,'item':copy.deepcopy(item),'count':count,
            'consume_items':False,'only_from_crafting':False}

def link(key,target,x,y,size=.85):
    return {'id':ident('link',key),'linked_quest':target,'x':float(x),'y':float(y),'shape':'rsquare','size':size}

def deco(a,b):return {'nodes':['q:'+format(int(a,16),'x'),'q:'+format(int(b,16),'x')]}

def old_icon(q):
    icon=q.get('icon','');return icon.get('id','') if isinstance(icon,dict) else icon

def core_graph(core,audit,filter_ids):
    resource_map={key:key for key in core}
    resource_map.update({key:'#forge:stripped_logs' for key in filter_ids})
    evidence=[];parents=defaultdict(set)
    for key,quest in core.items():
        if key not in audit['items']:continue
        route=selected(key,audit)
        grouped=defaultdict(list)
        for index,slot in enumerate(route['inputs']):
            for option in slot.get('options',[]):
                source=resource_map.get(option['id'])
                if source and source!=key:grouped[source].append(index)
        for source,slots in grouped.items():
            parents[key].add(source)
            evidence.append({'fromQuestId':core[source]['id'],'toQuestId':quest['id'],'itemId':source,
                             'fromItem':source,'toItem':key,'kind':'ingredient',
                             'relation':'ingredient','recipeId':route['id'],'slotIndexes':sorted(set(slots))})
        for source in route.get('machines',[]) or ([route['machine']] if route.get('machine') else []):
            if source in core and source!=key:
                parents[key].add(source)
                evidence.append({'fromQuestId':core[source]['id'],'toQuestId':quest['id'],'itemId':source,
                                 'fromItem':source,'toItem':key,'kind':'processing_machine',
                                 'relation':'machine','recipeId':route['id'],'slotIndexes':[]})
    for key,quest in core.items():
        if parents[key]:quest['dependencies']=[core[parent]['id'] for parent in sorted(parents[key])]
    return parents,evidence

def hidden_transitive_edges(parents,core):
    memo={}
    def ancestors(key):
        if key not in memo:
            memo[key]=set(parents[key])|set().union(*(ancestors(parent) for parent in parents[key]))
        return memo[key]
    hidden=[]
    for child,values in parents.items():
        for parent in sorted(values):
            if any(parent in ancestors(other) for other in values if other!=parent):
                hidden.append({'source':'q:'+format(int(core[child]['id'],16),'x'),
                               'dependency':'q:'+format(int(core[parent]['id'],16),'x'),'reveal_on_hover':False})
    return hidden

def layout_core(core,parents):
    """Layer the actual recipe DAG; raw metals enter together beside the press tier."""
    depth={};visiting=set()
    minimum={'#forge:stripped_logs':1,'minecraft:iron_block':2,'minecraft:iron_ingot':3,
             'minecraft:gold_ingot':3,'minecraft:copper_ingot':3,'create:sail_frame':2,'create:sand_paper':3}
    def visit(key):
        if key in visiting:raise ValueError('Recipe DAG cycle: '+key)
        if key in depth:return depth[key]
        visiting.add(key)
        value=max([minimum.get(key,0)]+[visit(parent)+1 for parent in parents[key]])
        visiting.remove(key);depth[key]=value;return value
    for key in core:visit(key)
    layers=defaultdict(list)
    for key in core:layers[depth[key]].append(key)
    priority=['minecraft:andesite','minecraft:iron_nugget','create:andesite_alloy','create:shaft',
              'create:hand_crank','create:water_wheel','create:mechanical_press','thermal:iron_plate',
              'thermal:gold_plate','create:whisk','create:mechanical_mixer','create:wrench','create:goggles']
    rank={key:i for i,key in enumerate(priority)}
    ys={}
    for layer in sorted(layers):
        keys=sorted(layers[layer],key=lambda key:(sum(ys.get(p,0) for p in parents[key])/max(len(parents[key]),1),rank.get(key,50),key))
        for i,key in enumerate(keys):ys[key]=(i-(len(keys)-1)/2)*2.1
    children=defaultdict(list)
    for child,values in parents.items():
        for parent in values:children[parent].append(child)
    for _ in range(5):
        for direction in [list(sorted(layers,reverse=True)),list(sorted(layers))]:
            for layer in direction:
                def center(key):
                    neighbors=children[key]+list(parents[key])
                    return sum(ys[n] for n in neighbors)/max(len(neighbors),1)
                keys=sorted(layers[layer],key=lambda key:(center(key),rank.get(key,50),key))
                for i,key in enumerate(keys):ys[key]=(i-(len(keys)-1)/2)*2.1
    # Foundation is read first; iron and gold remain side by side, not a resource chain.
    if set(core)!=set(CORE_LAYOUT):raise ValueError('Core layout requires review after changing core items')
    for key,q in core.items():q.update(x=CORE_LAYOUT[key][0],y=CORE_LAYOUT[key][1])
    return depth

def bounds(obj):
    return (obj['x']-obj.get('size',1)*128/144,obj['x']+obj.get('size',1)*128/144,
            obj['y']-obj.get('size',1)*74/144,obj['y']+obj.get('size',1)*74/144)

def overlap(a,b):
    aa,bb=bounds(a),bounds(b)
    return min(aa[1],bb[1])-max(aa[0],bb[0])>.03 and min(aa[3],bb[3])-max(aa[2],bb[2])>.03

def segment_box(a,b,r):
    low,high=0.,1.;box=bounds(r)
    for axis,left,right in [('x',box[0],box[1]),('y',box[2],box[3])]:
        delta=b[axis]-a[axis]
        if abs(delta)<1e-10:
            if a[axis]<=left or a[axis]>=right:return False
        else:
            v,w=(left-a[axis])/delta,(right-a[axis])/delta
            if v>w:v,w=w,v
            low,high=max(low,v),min(high,w)
            if low>=high:return False
    return low<high and high>0 and low<1

def place_reference(q,anchor,objects,edges):
    """Place tiny optional reference cards close to the actual relevant item."""
    candidates=[]
    for dx in [0.,1.6,-1.6,3.2,-3.2,4.8,-4.8]:
        for dy in range(1,19):
            for sign in [-1,1]:candidates.append((dx,sign*(1.5+dy*.95)))
    candidates.sort(key=lambda p:p[0]*p[0]+p[1]*p[1])
    for dx,dy in candidates:
        q.update(x=anchor['x']+dx,y=anchor['y']+dy)
        if any(overlap(q,obj) for obj in objects):continue
        if any(segment_box(a,b,q) for a,b in edges):continue
        if any(segment_box(anchor,q,obj) for obj in objects if obj['id']!=anchor['id']):continue
        return True
    # Dense corners may have no clear spoke. Keep the card near its related item anyway.
    for dx,dy in candidates:
        q.update(x=anchor['x']+dx,y=anchor['y']+dy)
        if not any(overlap(q,obj) for obj in objects) and not any(segment_box(a,b,q) for a,b in edges):return False
    q.update(x=anchor['x'],y=max(obj['y'] for obj in objects)+1.3)
    return False

def reference_anchor(q,core):
    item=old_icon(q)
    explicit={
      'create:vertical_gearbox':'create:gearbox','create:encased_chain_drive':'create:shaft',
      'create:adjustable_chain_gearshift':'create:gearshift','create:rotation_speed_controller':'create:gearbox',
      'create:sequenced_gearshift':'create:gearshift','create:flywheel':'create:shaft',
      'create:steam_engine':'create:fluid_tank','create:steam_whistle':'create:fluid_tank',
      'create:crushing_wheel':'create:millstone','create:deployer':'create:mechanical_mixer',
      'create:mechanical_crafter':'create:mechanical_mixer','create:brass_casing':'create:copper_casing',
      'create:empty_blaze_burner':'create:basin','create:blaze_burner':'create:basin',
      'create:red_sand_paper':'create:sand_paper','create:copper_valve_handle':'create:hand_crank',
      'create:fluid_valve':'create:fluid_pipe','create:smart_fluid_pipe':'create:fluid_pipe',
      'create:hose_pulley':'create:mechanical_pump','create:nozzle':'create:encased_fan',
      'create:creative_fluid_tank':'create:fluid_tank','create:creative_motor':'create:shaft',
      'create:andesite_ladder':'create:andesite_casing','create:andesite_scaffolding':'create:andesite_casing',
      'create:brown_toolbox':'create:wrench','create:clipboard':'create:wrench',
    }
    if item in explicit:return core[explicit[item]]
    if 'backtank' in item or 'diving' in item:return core['create:fluid_tank']
    if item in {'create:extendo_grip','create:potato_cannon'}:return core['create:wrench']
    if 'schematic' in item:return core['create:wrench']
    if item in {'create:analog_lever','create:redstone_link','create:powered_latch','create:powered_toggle_latch',
                'create:pulse_repeater','create:pulse_extender','create:pulse_timer','create:rose_quartz_lamp',
                'minecraft:lectern','create:linked_controller'}:return core['create:clutch']
    if any(t in item for t in ['piston','gantry','pulley','chassis','bearing','sticker','redstone_contact']):return core['create:gearshift']
    return core['create:andesite_casing']

def build(data,current,audit,items):
    original={q['id']:q for d in data['chapters'].values() for q in d['quests']}
    by_item={old_icon(q):q for q in original.values()}
    selected_old=[key for key in audit['core32'] if key not in {'create:crushing_wheel','create:deployer'}]+['create:sail_frame']
    stack,filter_ids=filter_stack(audit)
    core={};conversions=[];new_nodes=[]
    for key in selected_old:
        source=by_item[key];route=selected(key,audit);q=copy.deepcopy(source)
        name=NAMES.get(key,audit['items'][key]['name']);q['tasks']=[task(q['id'],source['tasks'][0]['id'],key,name)]
        q.update(title=name,shape='rsquare',size=1.05,optional=key in OPTIONAL_CORE,
                 description=recipe_description(key,audit,route)+source['description'])
        q.pop('subtitle',None);q.pop('dependencies',None);core[key]=q
        conversions.append({'questId':q['id'],'taskId':q['tasks'][0]['id'],'item':key,'count':1,'selectedRecipeId':route['id']})
    for key in NEW_ITEMS:
        item=stack if key.startswith('#') else key
        icon='minecraft:stripped_oak_log' if key.startswith('#') else key
        name='去皮原木' if key.startswith('#') else NAMES.get(icon,items[icon].get('n',icon))
        q={'id':ident('quest',key),'title':name,'icon':icon,'shape':'rsquare','size':1.05,
           'tasks':[task('',ident('task',key),item,name)],'description':[]}
        selected_id=None
        if key in audit['items']:
            route=selected(key,audit);selected_id=route['id'];q['description']=recipe_description(key,audit,route)
        elif key.startswith('#'):
            q['description']=['准备一块去皮原木，用安山合金应用在原木上制作安山机壳；铜机壳使用对应铜材料。',
                              '使用配方支持的去皮原木，不限定橡木。先用斧头为原木去皮，再拿对应材料对准放置的原木使用。']
        else:
            q['description']=[f'准备{name}，用于接下来的零件制作与加工。',
                              '']
        core[key]=q
        contract={'questId':q['id'],'taskId':q['tasks'][0]['id'],'item':copy.deepcopy(item),'count':1,'selectedRecipeId':selected_id}
        if key.startswith('#'):
            verified=audit['tagInputGroups']['forge:stripped_logs']['verifiedViaRecipeId']
            contract.update(matchTag='forge:stripped_logs',matchedItemIds=filter_ids,selectedRecipeId=verified,
                            verifiedViaRecipeId=verified,recipeOutputItem='create:andesite_casing')
        new_nodes.append(contract)
    parents,evidence=core_graph(core,audit,filter_ids);depth=layout_core(core,parents)
    core['create:mechanical_press']['size']=1.25
    core['create:mechanical_mixer']['size']=1.2
    core['create:encased_fan']['size']=1.2
    factory=copy.deepcopy(current[MAIN]);factory.update(title='机械动力起步',group=MAIN_GROUP,order_index=1,
       icon='create:andesite_alloy',consume_items=False,quests=list(core.values()),quest_links=[],quest_enhance_decorative_lines=[])
    hidden=hidden_transitive_edges(parents,core)
    factory['quest_enhance_hidden_dependency_lines']=hidden
    factory['images']=[
       {'x':4.0,'y':-18.0,'width':12.0,'height':1.0,'order':-1,'alpha':255,'click':'quest_enhance:text:配方主线'},
       {'x':10.0,'y':17.2,'width':22.0,'height':1.0,'order':-1,'alpha':255,'click':'quest_enhance:text:物品操作参考（按需查阅）'},
    ]
    hidden_pairs={(int(line['dependency'][2:],16),int(line['source'][2:],16)) for line in hidden}
    objects=list(core.values());edges=[(core[p],core[c]) for c,ps in parents.items() for p in ps
                                     if (int(core[p]['id'],16),int(core[c]['id'],16)) not in hidden_pairs]
    operational=[]
    for source in ['create:hand_crank','create:water_wheel','create:windmill_bearing','create:depot']:
        target='create:mechanical_press'
        operational.append({'fromQuestId':core[source]['id'],'toQuestId':core[target]['id'],
                            'fromItem':source,'toItem':target,'kind':'operational_reference',
                            'condition':'任选动力输入' if source!='create:depot' else '冲压时的物品承台，可按配方改用盆'})
        clear=not any(segment_box(core[source],core[target],obj) for obj in objects if obj['id'] not in (core[source]['id'],core[target]['id']))
        operational[-1]['drawn']=clear
        if clear:
            factory['quest_enhance_decorative_lines'].append(deco(core[source]['id'],core[target]['id']))
            edges.append((core[source],core[target]))
    mappings=[];unconnected=[]
    original_factory=[q for q in current[MAIN]['quests'] if q['id'] in original]
    for old in original_factory:
        if old_icon(old) in selected_old:continue
        q=copy.deepcopy(original[old['id']]);anchor=reference_anchor(q,core)
        q.update(optional=True,shape='rsquare',size=.65,
                 description=q['description'])
        q.pop('dependencies',None);q.pop('subtitle',None)
        if old_icon(q) in LATE:
            q['description'].insert(0,'所需构件与材料可在“汽鸣铁道”和“精智元件”中准备。')
        index=len(mappings)
        q.update(x=(index%15)*1.9,y=19.5+(index//15)*1.2)
        unconnected.append(q['id'])
        factory['quests'].append(q);objects.append(q)
        mappings.append({'questId':q['id'],'relatedQuestId':anchor['id']})
    documents={MAIN:factory};topic_milestones=[];topic_changes=[]
    for name in FILES[1:]:
        d=copy.deepcopy(current[name]);d['consume_items']=False
        d['quest_links']=[]
        for q in d['quests']:
            if q['id'] in original:
                raw=original[q['id']];q['tasks']=copy.deepcopy(raw['tasks']);q['icon']=copy.deepcopy(raw['icon'])
                q['description']=['']+copy.deepcopy(raw['description'])
                q['optional']=True
            else:topic_milestones.append(q['id'])
        roots=[q for q in d['quests'] if q['id'] not in original]
        root=roots[0]
        if 'logistics' in name:
            root['dependencies']=[core['create:depot']['id'],core['create:mechanical_press']['id']]
            root['description']=[p.replace('建厂主线的可停机工位','置物台与动力冲压工位') for p in root['description']]
            arm=roots[-1];arm['dependencies']=[OLD_IDS['precision']]
            d['quest_links']=[link('logistics-return-depot',core['create:depot']['id'],-3.5,0),
                              link('logistics-return-press',core['create:mechanical_press']['id'],-3.5,-2),
                              link('logistics-precision',OLD_IDS['precision'],22.5,-2),
                              link('logistics-brass',OLD_IDS['brass'],7.5,6)]
            root['description']=[p.replace('前面的基础运输和包裹订单','基础运输和包裹订单') for p in root['description']]
            roots[-1]['description']=[p.replace('主线精密阶段','精智元件的精密构件任务') for p in roots[-1]['description']]
            anchor=core['create:depot']
        elif 'structures' in name:
            root['dependencies']=[core['create:shaft']['id']]
            root['description']=[p.replace('从持续水力阶段接出','从传动杆与结构部件接出；动力可选择手摇、水力或风力') for p in root['description']]
            d['quest_links']=[link('agriculture-return',core['create:shaft']['id'],-3.5,0)]
            anchor=core['create:shaft']
        else:
            root['dependencies']=[OLD_IDS['railway']]
            root['description']=[p.replace('从建厂工业/装配材料阶段接出，先完成可制作的铁路构件','从既有汽鸣铁道的铁路构件任务接出，完成所需材料') for p in root['description']]
            d['quest_links']=[link('trains-railway-component',OLD_IDS['railway'],-3.5,0),
                              link('trains-return',core['create:mechanical_press']['id'],-3.5,-2),
                              link('trains-kit','58F03784745D9151',2,5),link('trains-schedule','7C2BCD18D1BCEEC9',15,6),
                              link('trains-deposits','211642A0702308A1',22.5,4)]
            anchor=core['create:mechanical_press']
        topic_changes.append({'questId':root['id'],'dependencies':root['dependencies']})
        # Navigation stays in one panel to the right of the recipe graph.
        index=len(factory['quest_links'])
        destination=link('factory-topic-'+name,root['id'],32+(index%2)*3.2,(index//2)*3.0)
        objects.append(destination)
        factory['quest_links'].append(destination)
        documents[name]=d
    # Old progression is referenced in place, not duplicated as new ingredient tasks.
    for key,target in OLD_IDS.items():
        index=len(factory['quest_links'])
        obj=link('factory-old-'+key,target,32+(index%2)*3.2,(index//2)*3.0)
        objects.append(obj);factory['quest_links'].append(obj)
    removed=[q['id'] for q in current[MAIN]['quests'] if q['id'] not in original]
    return documents,{'originalTaskConversions':conversions,'newMaterialQuests':new_nodes,
       'oldMilestonesRemoved':removed,'preservedTopicMilestones':topic_milestones,'dependencyEvidence':evidence,
       'topicDependencyChanges':topic_changes,'referenceMapping':mappings,'coreItems':list(core),
       'operationalReferences':operational,
       'hiddenTransitiveDependencyLines':copy.deepcopy(hidden),
       'referenceLayout':{'mode':'separate_grid','columns':15,'columnStep':1.9,'rowStep':1.2,'startY':19.5,
                          'coreReferenceDecorativeEdges':0,'navigationPanelX':[32.0,35.2]},
       'sourceMaterialAcquisition':[{'questId':core[key]['id'],'item':key,'source':'独立准备原料；不设置金属采集顺序或额外机器门槛','selectedRecipeId':None} for key in RAW_ITEMS],
       'coreQuestIds':[q['id'] for q in core.values()],'optionalCoreItems':sorted(OPTIONAL_CORE),
       'layoutDepth':{key:depth[key] for key in core},'unconnectedReferenceCards':unconnected}

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from walk(child)
    elif isinstance(value,list):
        for child in value:yield from walk(child)

def validate(documents,data,current,contract,items,loads):
    original={q['id']:q for d in data['chapters'].values() for q in d['quests']}
    new={q['id']:q for d in documents.values() for q in d['quests']}
    conversion={x['questId']:x for x in contract['originalTaskConversions']}
    if not original.keys()<=new.keys():raise ValueError('Original tutorial removed')
    for key,source in original.items():
        q=new[key]
        for field in ['icon','rewards']:
            if q.get(field)!=source.get(field):raise ValueError('Original '+field+' changed: '+key)
        if q['description'][-len(source['description']):]!=source['description']:raise ValueError('Original description suffix changed')
        if key in conversion:
            t=q['tasks'][0];c=conversion[key]
            if len(q['tasks'])!=1 or t['id']!=source['tasks'][0]['id'] or t['type']!='item' or t['item']!=c['item']:raise ValueError('Conversion mismatch')
            if t['consume_items'] or t['only_from_crafting']:raise ValueError('Item acquisition must be non-consuming')
        elif q['tasks']!=source['tasks']:raise ValueError('Unapproved original task changed')
    if set(contract['oldMilestonesRemoved'])&new.keys():raise ValueError('Abstract factory milestone retained')
    for key in contract['preservedTopicMilestones']:
        source=next(q for d in current.values() for q in d['quests'] if q['id']==key)
        if new[key]['tasks']!=source['tasks']:raise ValueError('Topic acceptance task changed')
    outside={}
    for file in LIVE.glob('*.snbt'):
        if file.name not in FILES:
            for obj in walk(loads(file.read_text())):
                if re.fullmatch('[0-9A-Fa-f]{16}',str(obj.get('id',''))):outside[obj['id']]=file.name
    objects=[obj for d in documents.values() for obj in walk(d) if re.fullmatch('[0-9A-Fa-f]{16}',str(obj.get('id','')))]
    ids=[obj['id'] for obj in objects]
    if len(ids)!=len(set(ids)) or set(ids)&outside.keys():raise ValueError('Object ID collision')
    all_targets=set(new)|set(outside)
    for d in documents.values():
        for q in d['quests']:
            if any(dep not in all_targets for dep in q.get('dependencies',[])):raise ValueError('Missing dependency target')
        for obj in d['quest_links']:
            if obj['linked_quest'] not in all_targets or int(obj['linked_quest'],16)>0x7fffffffffffffff:raise ValueError('Invalid QuestLink target')
    active=set();done=set()
    def visit(key):
        if key in active:raise ValueError('Dependency cycle')
        if key in done or key not in new:return
        active.add(key)
        for other in new[key].get('dependencies',[]):visit(other)
        active.remove(key);done.add(key)
    for key in new:visit(key)
    existing=set()
    for obj in objects:
        icon=obj.get('icon')
        if isinstance(icon,str) and ':' in icon:existing.add(icon)
        item=obj.get('item')
        if isinstance(item,str):existing.add(item)
        elif isinstance(item,dict) and 'id' in item:existing.add(item['id'])
    for value in contract['newMaterialQuests']:existing.update(value.get('matchedItemIds',[]))
    missing=sorted(existing-items.keys())
    if missing:raise ValueError('Item not in installed JEI catalog: '+str(missing))
    contract['existingItemIds']=sorted(existing)
    main=documents[MAIN];cards=main['quests']+main['quest_links'];byid={obj['id']:obj for obj in cards}
    hidden={(int(line['dependency'][2:],16),int(line['source'][2:],16)) for line in main['quest_enhance_hidden_dependency_lines']}
    visible=[(byid[edge['fromQuestId']],byid[edge['toQuestId']]) for edge in contract['dependencyEvidence']
             if (int(edge['fromQuestId'],16),int(edge['toQuestId'],16)) not in hidden]
    overlaps=[(a['id'],b['id']) for i,a in enumerate(cards) for b in cards[i+1:] if overlap(a,b)]
    through=[(a['id'],b['id'],r['id']) for a,b in visible for r in cards if r['id'] not in (a['id'],b['id']) and segment_box(a,b,r)]
    if overlaps or through:raise ValueError(f'Layout obstruction: overlaps={overlaps}, coreLinesThroughCards={through}')
    if any('translation{' in byid[key]['title'] for key in contract['coreQuestIds']):raise ValueError('Unreadable core title')
    return {'preservedQuestIds':len(original),'preservedTaskIds':sum(len(q['tasks']) for q in original.values()),
      'preservedDescriptionParagraphs':sum(len(q['description']) for q in original.values()),
      'itemTaskConversions':len(conversion),'newMaterialQuests':len(contract['newMaterialQuests']),
      'removedAbstractFactoryMilestones':len(contract['oldMilestonesRemoved']),
      'preservedTopicMilestones':len(contract['preservedTopicMilestones']),'totalQuestNodes':len(new),
      'coreItemNodes':len(contract['coreItems']),'recipeDependencyEdges':len(contract['dependencyEvidence']),
      'hiddenTransitiveDependencyEdges':len(hidden),'visibleCoreRecipeEdges':len(visible),
      'geometry':{'mainCardOverlaps':len(overlaps),'visibleCoreLinesThroughOtherCards':len(through)}}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--check',action='store_true');ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args();output=args.output.resolve();loads=parser()
    data,current,base=freeze(output,loads,args.check);audit=json.loads(AUDIT.read_text());items=catalog()
    docs,contract=build(data,current,audit,items)
    contract.update(schemaVersion=1,kind='create-recipe-spine-contract-v1',baseline=base,
       auditPath=AUDIT.relative_to(ROOT).as_posix(),auditSha256=sha(AUDIT.read_bytes()),
       chapterChanges={MAIN:{'id':docs[MAIN]['id'],'group':MAIN_GROUP,'order_index':1,'title':'机械动力起步'}},
       groupChanges=[TOPIC_GROUP],allowedTaskFieldsChanged=['type','item','count','consume_items','only_from_crafting','title'])
    report=validate(docs,data,current,contract,items,loads)
    report.update(kind='create-recipe-spine-draft-v1',mainRoot=ident('quest','minecraft:andesite'),
       chapters=[{'file':name,'id':d['id'],'title':d['title'],'group':d['group'],'quests':len(d['quests'])} for name,d in docs.items()],
       layout={'direction':'left-to-right','nominalLayerStep':4.5,'coreSize':1.05,'pressSize':1.25,'referenceSize':.65,
               'mainCapabilityY':1,'referenceGrid':contract['referenceLayout'],
               'machinePath':['create:andesite_alloy','create:andesite_casing','create:mechanical_press','thermal:iron_plate','create:whisk','create:mechanical_mixer']},
       recipePolicy='Actual selected recipe ingredients/machines; independent metal inputs; alternative routes stated in text.',
       referenceCardsWithoutSpokes=contract['unconnectedReferenceCards'])
    readme='''# 机械动力起步：配方任务草稿

从安山岩、铁粒开始，沿安山合金、机壳、传动与冲压能力展开。铁、金、铜是并行原料，板材和工具分支接实际冲压能力。全部核心为非消耗物品任务；不使用抽象工厂验收充当材料。

31张旧教程保留quest/task ID转换为item任务，13个材料/中间件新任务；其余旧教程保留原任务和完整601段正文后缀。大型水车与风力等是optional分支，不要求三种动力全做。粉碎轮、机械手及精密设备作为后续参考，连接原蒸汽/精智任务。

三个专题保留12个实建验收。主章移到主线组汽鸣之前，专题仍在“机械动力专题”。原9步抽象主干及可选蒸汽验收已撤掉；不修改玩家存档。旧阅读任务已完成的记录随ID保留，不把它当作新检测重新核验背包的证据。

主图只突出44个真实物品核心；75张optional操作参考统一在下方15列紧凑网格，保留相关物品正文和referenceMapping，不再从核心拉参考装饰线。跨章入口统一排在右侧。标题使用QuestEnhance原生画布文字，不添加假任务节点。

`source/current-chapters/`永久冻结改版前四章；`source/tutorial-baseline.json`冻结最初164教程。只生成本目录草稿，正式接入由独立安全部署器执行；不要再运行旧编排生成器覆盖此版本。

运行：`python3 tools/quest-workbench/build_create_recipe_spine.py`，随后加`--check`检验稳定输出。`contract.json`列转换白名单、移除节点、专题保留节点、每条核心依赖的已审计recipeId和slot证据。配方事实来自`tools/quest-workbench/evidence/create-recipe-spine-audit.json`及当前实际JEI导出。
'''
    blobs={Path('chapters')/name:snbt(d)+'\n' for name,d in docs.items()}
    blobs.update({Path('chapter_groups.fragment.snbt'):snbt({'chapter_groups':[TOPIC_GROUP]})+'\n',
      Path('contract.json'):json.dumps(contract,ensure_ascii=False,indent=2)+'\n',
      Path('report.json'):json.dumps(report,ensure_ascii=False,indent=2)+'\n',Path('README.md'):readme})
    for relative,blob in blobs.items():
        if relative.suffix=='.snbt':loads(blob)
        path=output/relative
        if args.check:
            if not path.exists() or path.read_text()!=blob:raise ValueError('Stale output: '+str(path))
        else:path.parent.mkdir(parents=True,exist_ok=True);path.write_text(blob)
    if set(p.name for p in (output/'chapters').glob('*.snbt'))!=set(FILES):raise ValueError('Unexpected draft chapter')
    print(json.dumps({'mode':'check' if args.check else 'generate',**report},ensure_ascii=False))

if __name__=='__main__':main()
