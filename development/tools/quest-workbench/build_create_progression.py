#!/usr/bin/env python3
"""Generate four Create build-progression drafts from a frozen 164-tutorial baseline.

This script never deploys quests. Use reorganize_create_progression.py for installation.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / 'design/create-progression-draft'
SOURCE = ROOT / 'clients/cmi-expedition/instance/config/ftbquests/quests/chapters'
SEED = 'cmi-expedition/create-progression/1.20.1/v1/'
GROUP = {'id': '6977257A15C2F0DE', 'title': '机械动力'}
CHAPTERS = {
    'factory': ('create_basics_orientation.snbt', '447F1A0F479DB44E', '建厂主线', 'create:mechanical_press'),
    'logistics': ('create_basics_create_logistics.snbt', '04EA7D06221B1F38', '物流与仓储', 'create:item_vault'),
    'agriculture': ('create_basics_structures.snbt', '07557E97A823C8CC', '农业与生产', 'create:mechanical_harvester'),
    'trains': ('create_basics_create_trains.snbt', '644A75DE0F765DC6', '铁路与运输', 'create:track_station'),
}
REFERENCE_NOTE = '自由参考：此卡保留原教程，只解释相关部件。无需逐卡勾选才能推进建厂主线；辅助线表示知识关联，不是制作或完成前置。'
MANUAL_NOTE = '让产线实际运行，完成下列目标后勾选完成。'
FACTORY_POSITIONS = {'plan':(0.,0.),'water':(7.5,0.),'plates':(15.,0.),'ore':(22.5,0.),
                     'fluids':(30.,0.),'materials':(37.5,0.),'precision':(45.,0.),
                     'expansion':(52.5,0.),'replicate':(60.,0.),'steam':(45.,6.)}

def ident(kind, key):
    value = int(hashlib.sha256((SEED + kind + '/' + key).encode()).hexdigest()[:16], 16)
    return f'{value & 0x7fffffffffffffff:016X}'

def snbt(value, depth=0):
    tab, child = '\t' * depth, '\t' * (depth + 1)
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool): return 'true' if value else 'false'
    if isinstance(value, int): return str(value)
    if isinstance(value, float): return repr(value) + 'd'
    if isinstance(value, list):
        if not value: return '[ ]'
        if len(value) <= 3 and all(isinstance(v, (str, int, bool)) for v in value):
            return '[' + ' '.join(snbt(v, depth) for v in value) + ']'
        return '[\n' + '\n'.join(child + snbt(v, depth + 1) for v in value) + '\n' + tab + ']'
    if isinstance(value, dict):
        if not value: return '{ }'
        return '{\n' + '\n'.join(child + (k if re.fullmatch(r'[\w.+-]+', k) else snbt(k)) + ': ' +
                                  snbt(v, depth + 1) for k, v in value.items()) + '\n' + tab + '}'
    raise TypeError(type(value))

def parser():
    spec = importlib.util.spec_from_file_location('create_progression_parser', ROOT / 'clients/cmi-expedition/tools/ftb_snbt.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.loads

def baseline(output, loads, check):
    path = output / 'source-inventory.json'
    if path.exists():
        data = json.loads(path.read_text())
    else:
        if check: raise ValueError('Frozen source-inventory.json missing; run generation once first')
        files = sorted(SOURCE.glob('create_basics_*.snbt'))
        if len(files) != 11: raise ValueError('Initial capture requires the original eleven chapters')
        data = {'kind': 'create-tutorial-baseline-v1', 'chapters': {p.name: loads(p.read_text()) for p in files},
                'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
        output.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    if sum(len(c.get('quests', [])) for c in data['chapters'].values()) != 164:
        raise ValueError('Frozen source must contain exactly164 original tutorials')
    return data

def stage(key, title, icon, *paragraphs, deps=None):
    return {'key': key, 'title': title, 'icon': icon, 'description': list(paragraphs), 'deps': deps}

def milestones():
    return {
      'factory': [
        stage('plan', '01 开工规划', 'create:wrench',
          '目标：划定第一间车间，准备扳手、护目镜、输入箱和成品箱。给轴线、加工区、管路与检修通道留位置；先做能运行的小单元，不必一次造完大厂。',
          '验收：明确一条原料入口和一条成品出口，能指出动力从哪里接入、哪里停机，以及未来物流和铁路从哪边扩建。',
          '本包基础机壳及多种早期设备有恢复的原生并行配方。先查当前配方选择材料路线，不要把所有基础机器都当成必须先造构件。下一步先让水力带动一台机器。'),
        stage('water', '02 持续水力', 'create:water_wheel',
          '目标：让水车经轴、齿轮或齿轮箱持续驱动石磨。先加工一小批有效原料，并从输出端收集产物。',
          '验收：断开手摇曲柄后仍能工作；停转时会检查水流、轴向、转向和应力。提高转速不等于提高动力容量，过载时应拆分负载或扩充动力。',
          '风车是可选的另一种持续动力；农业支线可从这一阶段接出，不需要先完成精密构件。下一步为冲压工位增加独立停机。'),
        stage('plates', '03 可停机工位', 'create:mechanical_press',
          '目标：搭一台动力冲压机与置物台工位，在分支轴上安装离合器。投入有效板材配方原料，压出并收集一批板材。',
          '验收：只停这一工位，其他动力仍可运行；复位后继续加工。能清楚找到输入、加工空间、输出与停机控制。',
          '这一步不要求动力臂或动力合成器。先用手工、漏斗或简单传送完成供料；物流与仓储专题从这里接出。下一步把批量粉碎和洗涤接起来。'),
        stage('ore', '04 粉碎与洗矿', 'create:crushing_wheel',
          '目标：将一对粉碎轮按正确轴向与相反转向运行，把当前配方允许的原料粉碎，再用鼓风机水洗并收集产物。先用小批量测试，确认不吞料再连续供料。',
          '验收：粉碎物能进入洗涤区域，风向正确，物品不会被吹散或堵在输出；能检查粉碎轮应力和洗涤时间。',
          '本包粉碎轮可在工作台逐个制作，成对使用不需要先造动力合成器。石磨与粉碎轮的配方并不完全相同。下一步建立稳定的流体工位。'),
        stage('fluids', '05 稳定供液', 'create:mechanical_pump',
          '目标：接好流体储罐、管道和动力泵，实际输送一批流体；再跑通一项当前配方允许的盆内加工或注液操作。',
          '验收：能辨认泵送方向、储量和管内流体；停止输入后不继续污染其他管路。需要容器排液时使用分液池，需要给物品注液时使用注液器。',
          '是否要加热、加热到什么级别以当前配方为准，普通搅拌并不一律要求烈焰人燃烧室。下一步把供液能力用于本包合金和早期蒸汽材料。'),
        stage('steam', '支线 早期蒸汽站', 'steampowered:bronze_boiler',
          '目标：接入本包蒸汽构件和合金材料路线，搭建一套SteamPowered青铜蒸汽站：燃烧室供热→上方锅炉供水→蒸汽进入青铜引擎→对应青铜飞轮输出。',
          '验收：补水、补燃料并带实际负载工作一段时间；确认用的是同材质SteamPowered飞轮，并按其结构要求在引擎前方匹配位置装好。缺少匹配飞轮时引擎输出为零。贴锅炉可低效起步，主动泵送蒸汽可提效。',
          '早期这套锅炉、燃烧室、引擎和配套飞轮无需精密构件。Create原版飞轮是另一件物品，不能替代其输出飞轮；精密后的Create蒸汽引擎也不是这套早期蒸汽站。',
          '这是一条可选动力支线，可以在精密构件前建设；没有要求先完成它才能进行精密装配或铁路运输。材料和通用装配准备见建厂06。', deps=[('factory','materials')]),
        stage('materials', '06 工业与装配备料', 'cmi:railway_mechanism',
          '目标：按本包现有蒸汽/精智任务准备熔融黄铜、工业铁、构件模具、适用齿轮半成品和机械构件零件。用一个物料箱或缓冲区把装配所需材料按工序分开。',
          '验收：逐个查当前配方并准备好一批装配材料及供液；电子管有铁板＋磨制玫瑰石英的直接制作路线，原有电子管装配路线也保留，不必把信素当成所有电子管的硬门槛。',
          '黄铜当前有熔融金属合金路线：270mB熔铜＋90mB熔锌→360mB熔黄铜，Create搅拌与匠魂合金可并行选择。热源与容器按当前配方确认，不按原生固体铜锌混锭或唯一烈焰路线套用。蒸汽构件等本包构件同样要先理解模具加工、注液和机械零件的通用装配，按当前配方准备。',
          '下界探索存在缺氧风险；按既有任务准备潜水头盔与已充气背罐等可用供氧方案，出发前检查空气。背罐制作后仍需接转动充气，不能把刚合成的空背罐当作已可用。',
          '铁路专题从工业/装配材料阶段接出：铁路构件涉及致密坚固板、熔融工业铁、半成品齿轮、黄铜板和机械零件；不直接要求Create蒸汽引擎或精密构件。早期SteamPowered站是此阶段的可选动力支线，不是铁路和精密的前置。',deps=[('factory','fluids')]),
        stage('precision', '07 魔改精密装配', 'create:precision_mechanism',
          '目标：搭建本包精密构件装配单元。以黄铜板起步，经Vintage Improvements曲线冲压机与构件模具加工、注入90mB熔融黄铜，再依次部署电子管、适用齿轮半成品和机械构件零件，收集精密构件。',
          '验收：按当前配方实际跑完一轮，半成品沿正确方向流转，输出不与未完成品混放；断料时能定位到缺少的步骤。不是原生金板五轮方案。',
          '曲线冲压机恢复了原生并行制作路线，不必先制造安山构件来解锁这台起步设备。动力合成器本身需要精密构件，不能反过来作为这一轮装配的强制前提。下一步再考虑用精密设备扩建。'),
        stage('expansion', '08 精密后扩建', 'create:mechanical_crafter',
          '目标：用已经产出的精密构件完成一项确有需要的扩建：动力合成器自动制作有效配方，或搭建精密后的Create蒸汽引擎动力网。两项任选其一，不需要为了验收重复造整套设备。',
          '验收：新工位能完成一批实际生产，或者新动力能带动已有工位；检查输入方向、输出与应力，并能独立停机。',
          '动力合成器在本包需要精密构件。Create蒸汽引擎需要蒸汽构件、精密构件等当前材料；它与前面的SteamPowered锅炉站不同。动力臂同样需要精密，物流专题的动力臂验收从这里的精密阶段接入。'),
        stage('replicate', '09 复制与扩容', 'create:schematicannon',
          '目标：先用蓝图记录一个已验证的小生产单元，再手工或用蓝图炮复制到第二处；给复制件接上真实动力、原料和输出。',
          '验收：第二个单元独立完成一批生产；缺料、管路串液、结构粘连和应力不足都已排除。蓝图只是建造说明，放下结构不等于工厂已经工作。',
          '按实际瓶颈选择扩大水力/蒸汽、增加物流缓冲、接农场或拉铁路。上下的结构、建筑与工具卡可随需要阅读，不必全打勾才算完成工厂。创造工具仅供认识，不是生存建造目标。'),
      ],
      'logistics': [
        stage('transfer', '01 箱到箱输送', 'create:belt_connector',
          '目标：从建厂主线的可停机工位接出，用传送带、溜槽或漏斗完成输入箱→加工工位→成品箱的一次自动输送。',
          '验收：原料不会掉落，输出塞满时能安全停止或缓冲，清空后可恢复。先用简单路线，不要求动力臂或包裹网络。', deps=[('factory', 'plates')]),
        stage('sort', '02 筛选与缓冲', 'create:brass_funnel',
          '目标：给实际工位增加筛选与缓冲，区分原料、成品和余料；用数量控制、隧道分流或库存检测避免持续堆料。',
          '验收：投入混合物料时仍能送到正确出口；至少验证一次缺料和满仓。黄铜设备按当前材料路线制作，不能把所有物流都误判为必须先有精密构件。'),
        stage('orders', '03 完成一份订单', 'create:packager',
          '目标：将仓库和一个需求工位接成小型包裹网络：配置库存链接、打包机和请求端，让一份真实订单从库存送到使用处并正确拆包。',
          '验收：地址匹配，缺货能识别，物品没有在错误仓库循环；可再接蛙港/链式传输和工厂仪表。',
          '打包机、库存链接、库存清单及工厂仪表在本包都有不消耗精密构件的路线。先查可用路线，不把动力臂当包裹网络的必要前提。'),
        stage('arm', '04 精密工位供料', 'create:mechanical_arm',
          '目标：已有精密构件后，用动力臂给一个真实工位补料，配置输入与输出目标，并与现有筛选和缓冲衔接。',
          '验收：连续运行几个周期，动力臂不会从错误容器取料或把产物送回输入；停机与缺料后可以恢复。',
          '这一项明确需要精密构件；前面的基础运输和包裹订单可以先做，不必等动力臂。这是从主线精密阶段接入的高级供料分支，无需先做包裹订单。', deps=[('factory', 'precision')]),
      ],
      'agriculture': [
        stage('assemble', '01 装配小农场', 'create:mechanical_bearing',
          '目标：从持续水力阶段接出，做一块小田和一个能正确旋转的收割结构。使用动力轴承、底盘或强力胶固定必要部件，并给可动范围留出空间。',
          '验收：装配后没有误粘车间，停机可安全复位，收割机朝向正确。先用小规模验证结构，不追求一次覆盖最大面积。', deps=[('factory', 'water')]),
        stage('harvest', '02 收获后回仓', 'create:portable_storage_interface',
          '目标：让收割结构实际收获一轮，并用移动存储接口在合适位置与固定端对接，把收获送入仓库。',
          '验收：接口到位能停靠并卸货，错位时能发现；收获物不会堆在结构内或掉在田里。接口不是隔空、跨维度的无限仓储。'),
        stage('cycles', '03 连续播收循环', 'create:mechanical_plough',
          '目标：按当前作物与结构能力安排耕地、种子和收割，连续运行几个周期；用结构控制器或红石触点完成需要的启停。',
          '验收：不会越种越少，不会反复破坏田地；缺种、满仓或断动力后知道如何恢复。不同作物能否由收割机处理，以实际操作和当前配方为准。'),
        stage('supply', '04 生产接入工厂', 'create:mechanical_saw',
          '目标：为工厂增加一条稳定的农业原料供应。可以选用现有农场作物进入石磨/加工线，或用动力锯建立小型木材供应。',
          '验收：实际获得并储存一批可供其他工位使用的原料，原料、种苗和副产物有各自出口；不会耗尽播种或补植库存。',
          '树木肥料和动力锯是按需求选用的扩建参考，不要求所有作物与树种都做一遍。'),
      ],
      'trains': [
        stage('connect', '01 两站连通', 'create:track_station',
          '目标：从建厂工业/装配材料阶段接出，先完成可制作的铁路构件，再连接两座有效车站并组装一列能手动驾驶的列车。',
          '验收：轨道连续，转向架与车厢装配正确，控制器可驾驶；先在短线路上测试，再铺到矿点。',
          '铁路构件不是Create蒸汽引擎的下游，也不直接吃精密构件；按本包当前致密坚固板、熔融工业铁、半成品齿轮、黄铜板与机械零件路线备料。', deps=[('factory', 'materials')]),
        stage('loading', '02 往返并装卸', 'create:portable_storage_interface',
          '目标：手动驾驶列车往返两站，并用移动存储接口完成一次货物装卸；需要液体运输时再选移动流体接口。',
          '验收：停靠位置能让接口对接，出发前装卸完成，返程后物品进入正确仓库。门、座位和车厢外壳按需要添加，不是每种都必须制作。'),
        stage('schedule', '03 自动班次', 'create:schedule',
          '目标：为已测试的列车设置时刻表和驾驶员，自动完成一轮到站、等待、装卸与返程。',
          '验收：至少完整运行一个班次；等待条件不会让列车立刻空跑，也不会永远等不到发车。先调通小线路再增加班次。'),
        stage('delivery', '04 矿点回厂', 'create:track_signal',
          '目标：按现有矿脉与运输任务，把至少一种远方原料稳定送回工厂。用信号机、侦测器和区间设计确保交会或共线处不会相撞。',
          '验收：资源从产地装车、按班次运输、卸入工厂原料仓；停运、缺货或区间占用时能判断原因。',
          '本包镍、银、钒等资源与矿脉探索有关，具体资源阶段继续看既有蒸汽/精智任务。包裹邮筒可以接入铁路运输，但不是所有铁路都必须承担邮政业务。'),
      ],
    }

def icon_name(quest):
    icon = quest.get('icon', '')
    return (icon.get('id', '') if isinstance(icon, dict) else icon).split(':', 1)[-1]

def assignment(name, quest):
    icon, qid = icon_name(quest), quest['id']
    if 'create_trains' in name: return 'trains'
    if icon in {'white_postbox', 'desk_bell', 'cart_assembler', 'minecart_coupling', 'controller_rail',
                'mechanical_roller', 'white_seat', 'portable_fluid_interface'}: return 'trains'
    if icon in {'mechanical_saw', 'tree_fertilizer', 'super_glue', 'radial_chassis', 'mechanical_bearing',
                'mechanical_harvester', 'mechanical_plough', 'contraption_controls', 'portable_storage_interface'} or qid == '3A24BF70CFEFF64A':
        return 'agriculture'
    if 'create_packages' in name: return 'logistics'
    if 'create_logistics' in name and icon not in {'brown_toolbox', 'depot'}: return 'logistics'
    if icon in {'display_link', 'display_board', 'nixie_tube', 'placard', 'stockpile_switch', 'content_observer'}:
        return 'logistics'
    return 'factory'

STAGE_ICONS = {
 'factory': [
  {'wrench','goggles','andesite_casing','andesite_ladder','andesite_scaffolding','brown_toolbox','clipboard','crafting_blueprint'},
  {'shaft','cogwheel','large_cogwheel','gearbox','vertical_gearbox','hand_crank','water_wheel','large_water_wheel','windmill_bearing','sail_frame','white_sail','millstone'},
  {'mechanical_press','depot','clutch','gearshift','encased_chain_drive','adjustable_chain_gearshift','analog_lever','powered_latch','powered_toggle_latch'},
  {'crushing_wheel','encased_fan','mechanical_drill','speedometer','stressometer','pulse_repeater','pulse_extender','pulse_timer'},
  {'copper_casing','fluid_pipe','mechanical_pump','fluid_valve','smart_fluid_pipe','fluid_tank','spout','item_drain','hose_pulley','nozzle','copper_valve_handle','mechanical_mixer','basin','creative_fluid_tank'},
  {'steam_whistle','empty_blaze_burner','blaze_burner','copper_backtank','copper_diving_helmet','copper_diving_boots'},
  {'brass_casing','sand_paper','red_sand_paper','redstone_link','rose_quartz_lamp','lectern','linked_controller','extendo_grip','potato_cannon'},
  {'deployer','linear_chassis','secondary_linear_chassis','mechanical_piston','sticky_mechanical_piston','piston_extension_pole','rope_pulley','gantry_shaft','gantry_carriage','sticker'},
  {'mechanical_crafter','steam_engine','flywheel','rotation_speed_controller','sequenced_gearshift','elevator_pulley','redstone_contact','netherite_backtank','netherite_diving_helmet','netherite_diving_boots','creative_motor'},
  {'schematic_and_quill','empty_schematic','schematic_table','schematic','schematicannon','cuckoo_clock','peculiar_bell','haunted_bell','wand_of_symmetry','handheld_worldshaper','clockwork_bearing','turntable','andesite_door','brass_door','copper_door','framed_glass_door','framed_glass_trapdoor','copycat_step','copycat_panel'},
 ],
 'logistics': [
  {'belt_connector','andesite_funnel','andesite_tunnel','chute','item_hatch'},
  {'brass_funnel','brass_tunnel','smart_chute','weighted_ejector','item_vault','filter','attribute_filter','stockpile_switch','content_observer','placard'},
  {'packager','repackager','package_frogport','chain_conveyor','stock_link','stock_ticker','redstone_requester','factory_gauge','white_table_cloth','package_filter','display_link','display_board','nixie_tube','creative_crate'},
  {'mechanical_arm'},
 ],
 'agriculture': [
  {'mechanical_bearing','super_glue','radial_chassis'},
  {'mechanical_harvester','portable_storage_interface'},
  {'mechanical_plough','contraption_controls','redstone_contact'},
  {'mechanical_saw','tree_fertilizer'},
 ],
 'trains': [
  {'track','track_station','controls','railway_casing','cart_assembler','minecart_coupling','controller_rail'},
  {'portable_fluid_interface','train_door','train_trapdoor','white_seat'},
  {'schedule','desk_bell'},
  {'track_signal','track_observer','white_postbox','mechanical_roller'},
 ],
}

def reference_stage(chapter, quest):
    icon = icon_name(quest)
    hits = [i for i, names in enumerate(STAGE_ICONS[chapter]) if icon in names]
    if not hits: raise ValueError(f'Unassigned reference stage: {quest["id"]} {icon}')
    return hits[0]

def qid(chapter, key): return ident('quest', chapter + '/' + key)

def make_milestone(chapter, index, definition, stages):
    key = definition['key']
    deps = definition['deps']
    if deps is None: deps = [(chapter, stages[index - 1]['key'])] if index else []
    x,y=FACTORY_POSITIONS[key] if chapter=='factory' else (index*7.5,0.0)
    quest = {'id': qid(chapter, key), 'title': definition['title'], 'icon': definition['icon'],
             'shape': 'rsquare', 'size': 1.3, 'x': x, 'y': y,
             'description': [MANUAL_NOTE] + definition['description'],
             'tasks': [{'id': ident('task', chapter + '/' + key), 'type': 'checkmark', 'title': '已实建并通过验收'}]}
    if deps: quest['dependencies'] = [qid(c, k) for c, k in deps]
    if chapter=='factory' and key=='steam':quest['optional']=True
    return quest

def deco(a, b): return {'nodes': ['q:' + f'{int(a,16):x}', 'q:' + f'{int(b,16):x}']}

def link(chapter, key, target, x, y):
    return {'id': ident('link', chapter + '/' + key), 'linked_quest': target,
            'x': float(x), 'y': float(y), 'shape': 'rsquare', 'size': 0.85}

# Existing content is linked for recipes/progression, never copied or modified.
OLD_LINKS = {
 'factory': [('alloy','2F00DD29F68238BA',41.,11.5),('steam-component','5BB078BA5116FE68',43.,11.5),
             ('steam-boiler','12CEF39F02D4EB3A',45.,11.5),('steam-output','5227B74E4F8FF3F5',47.,11.5),
             ('industrial-iron','17DC0AE5C56048CF',37.5,-5.5),('electronics','095B15FB9AA8B9AB',39.5,-5.5),
             ('precision-recipe','1570B04A1D692BCC',45.,-5.5)],
 'logistics': [('brass','2F00DD29F68238BA',7.5,6.0),('precision','1570B04A1D692BCC',22.5,4.0)],
 'agriculture': [],
 'trains': [('railway-component','6BA8D6727D497F84',0.0,5.0),('train-kit','58F03784745D9151',2.0,5.0),
            ('schedule','7C2BCD18D1BCEEC9',15.0,6.0),('deposits','211642A0702308A1',22.5,4.0)],
}

def generate(data):
    definitions = milestones()
    buckets = defaultdict(list)
    for name, document in data['chapters'].items():
        for quest in document['quests']:
            chapter = assignment(name, quest)
            buckets[chapter].append((name, quest))
    counts = {c:len(buckets[c]) for c in CHAPTERS}
    if counts != {'factory':106,'logistics':30,'agriculture':10,'trains':18}: raise ValueError(counts)
    documents, mappings = {}, []
    for order, (chapter, (filename, chapter_id, title, icon)) in enumerate(CHAPTERS.items()):
        stages = definitions[chapter]
        main = [make_milestone(chapter, i, d, stages) for i,d in enumerate(stages)]
        document = {'id':chapter_id, 'filename':Path(filename).stem, 'group':GROUP['id'], 'title':title, 'icon':icon,
                    'order_index':order, 'default_hide_dependency_lines':False, 'progression_mode':'flexible',
                    'quests':main, 'quest_links':[], 'quest_enhance_decorative_lines':[]}
        grouped = defaultdict(list)
        for source, original in buckets[chapter]: grouped[reference_stage(chapter, original)].append((source, original))
        for i, references in grouped.items():
            # Each column is a short reading branch, not a completion chain.
            previous = {}
            for n, (source, original) in enumerate(references):
                branch = chapter=='factory' and stages[i]['key']=='steam'
                side = 1 if branch or n%2 else -1
                slot = n if branch else n//2
                column, row = slot % 3, slot // 3
                quest = copy.deepcopy(original)
                quest.pop('dependencies', None)
                quest.update({'x':main[i]['x']+(column-1)*1.9, 'y':main[i]['y']+side*(2.25+row*1.25), 'shape':'rsquare', 'size':0.8,
                              'optional':True,
                              'subtitle':f'参考 · {stages[i]["title"]}',
                              'description':[f'阶段位置：{title} / {stages[i]["title"]}。',REFERENCE_NOTE]+copy.deepcopy(original['description'])})
                # Keep the real materials→optional steam branch clear of this reference card.
                if quest['id']=='302A7FDFABBFA5E3':quest['y']=4.75
                document['quests'].append(quest)
                ancestor = previous.get((side,column), main[i]['id'])
                document['quest_enhance_decorative_lines'].append(deco(ancestor, quest['id']))
                previous[(side,column)] = quest['id']
                mappings.append({'questId':quest['id'],'source':source,'chapter':filename,
                                 'stage':stages[i]['key'],'stageQuestId':main[i]['id'],'icon':original['icon']})
        if chapter == 'factory':
            for topic, anchor in [('agriculture','water'),('logistics','plates'),('trains','materials')]:
                index = next(i for i,s in enumerate(stages) if s['key']==anchor)
                document['quest_links'].append(link(chapter,topic+'-topic',qid(topic,definitions[topic][0]['key']),main[index]['x']+3.75,1.75))
        else:
            anchor = {'logistics':'plates','agriculture':'water','trains':'materials'}[chapter]
            document['quest_links'].append(link(chapter,'return-factory',qid('factory',anchor),-3.5,0.0))
            if chapter == 'logistics':
                document['quest_links'].append(link(chapter,'factory-precision',qid('factory','precision'),22.5,-2.0))
        for key,target,x,y in OLD_LINKS[chapter]: document['quest_links'].append(link(chapter,key,target,x,y))
        documents[filename] = document
    return documents,mappings

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values(): yield from walk(child)
    elif isinstance(value,list):
        for child in value: yield from walk(child)

def geometry(documents, outside_quests):
    """Check the editor's card rectangles, including dependencies drawn via links."""
    all_quests={q['id']:q for d in documents.values() for q in d['quests']}
    all_quests.update(outside_quests)
    def segment_box(a,b,r):
        low,high=0.,1.
        for axis,scale in [('x',128/144),('y',74/144)]:
            start,end=a[axis],b[axis]
            left,right=r[axis]-r['size']*scale,r[axis]+r['size']*scale
            delta=end-start
            if abs(delta)<1e-12:
                if start<=left or start>=right:return False
            else:
                v,w=(left-start)/delta,(right-start)/delta
                if v>w:v,w=w,v
                low,high=max(low,v),min(high,w)
                if low>=high:return False
        return low<high and high>0 and low<1
    def cross(a,b,c,d):
        def orient(p,q,r):return (q['x']-p['x'])*(r['y']-p['y'])-(q['y']-p['y'])*(r['x']-p['x'])
        return orient(a,b,c)*orient(a,b,d)<-1e-10 and orient(c,d,a)*orient(c,d,b)<-1e-10
    result={}
    for filename,document in documents.items():
        objects=document['quests']+document['quest_links']; providers=defaultdict(list);edges=[]
        for obj in objects:providers[obj.get('linked_quest',obj['id'])].append(obj)
        for obj in objects:
            target=all_quests[obj.get('linked_quest',obj['id'])]
            for dep in target.get('dependencies',[]):
                edges.extend((source,obj) for source in providers.get(dep,[]))
        for line in document['quest_enhance_decorative_lines']:
            a,b=[f'{int(value[2:],16):016X}' for value in line['nodes']]
            edges.append((providers[a][0],providers[b][0]))
        overlap=[];nodecross=[];edgecross=[]
        for i,a in enumerate(objects):
            for b in objects[i+1:]:
                if abs(a['x']-b['x'])<(a['size']+b['size'])*128/144 and abs(a['y']-b['y'])<(a['size']+b['size'])*74/144:
                    overlap.append([a['id'],b['id']])
        for i,(a,b) in enumerate(edges):
            for r in objects:
                if r['id'] not in (a['id'],b['id']) and segment_box(a,b,r):nodecross.append([a['id'],b['id'],r['id']])
            for c,d in edges[i+1:]:
                if len({a['id'],b['id'],c['id'],d['id']})==4 and cross(a,b,c,d):edgecross.append([a['id'],b['id'],c['id'],d['id']])
        if overlap or nodecross or edgecross:raise ValueError(f'Geometry {filename}: overlap={overlap}, nodecross={nodecross}, edgecross={edgecross}')
        result[filename]={'cardOverlaps':0,'edgeCrossings':0,'linesThroughOtherCards':0,'visibleEdgesIncludingQuestLinks':len(edges)}
    return result

def validate(data, documents):
    old = {q['id']:q for d in data['chapters'].values() for q in d['quests']}
    new = {q['id']:q for d in documents.values() for q in d['quests']}
    ids = [v['id'] for d in documents.values() for v in walk(d) if re.fullmatch('[0-9A-Fa-f]{16}',str(v.get('id','')))]
    if len(ids)!=len(set(ids)): raise ValueError('Duplicate generated object ID')
    for key, original in old.items():
        quest = new[key]
        for field in ('tasks','rewards','icon'):
            if quest.get(field)!=original.get(field): raise ValueError(f'Original {field} changed: {key}')
        if quest['description'][-len(original['description']):]!=original['description']:
            raise ValueError(f'Original description suffix changed: {key}')
        if quest.get('dependencies'): raise ValueError('Reference reading gained a completion dependency')
        if quest.get('optional') is not True: raise ValueError('Reference reading must not count toward chapter progression')
    for key in new.keys()-old.keys():
        if int(key,16)>0x7fffffffffffffff: raise ValueError('New ID not signed63-bit')
        if new[key].get('rewards') or any(t['type']!='checkmark' for t in new[key]['tasks']):
            raise ValueError('New milestone changes rewards or detection policy')
    outside = {};outside_quests={}
    for file in SOURCE.glob('*.snbt'):
        if not file.name.startswith('create_basics_'):
            d=parser()(file.read_text())
            outside_quests.update({q['id']:q for q in d.get('quests',[])})
            for v in walk(d):
                if re.fullmatch('[0-9A-Fa-f]{16}',str(v.get('id',''))): outside[v['id'].upper()]=file.name
    if set(ids)&set(outside): raise ValueError('Generated object ID collides outside the tutorial family')
    visible_deps=0
    for filename,d in documents.items():
        nodes={q['id']:q for q in d['quests']}
        for line in d['quest_enhance_decorative_lines']:
            for ref in line['nodes']:
                if not re.fullmatch(r'q:[1-9a-f][0-9a-f]*',ref) or f'{int(ref[2:],16):016X}' not in nodes:
                    raise ValueError('Invalid local decorative reference')
        for q in nodes.values():
            for dependency in q.get('dependencies',[]):
                if dependency not in new: raise ValueError('Unknown new dependency')
                visible_deps+=1
        for l in d['quest_links']:
            if l['linked_quest'] not in new and l['linked_quest'] not in outside: raise ValueError('Missing link target')
            if int(l['linked_quest'],16)>0x7fffffffffffffff: raise ValueError('QuestLink target exceeds signed63-bit')
    active,done=set(),set()
    def visit(key):
        if key in active: raise ValueError('Dependency cycle')
        if key in done:return
        active.add(key)
        for other in new[key].get('dependencies',[]):visit(other)
        active.remove(key);done.add(key)
    for key in new:visit(key)
    return {'preservedQuestIds':len(old),'preservedTaskIds':sum(len(q['tasks']) for q in old.values()),
            'preservedDescriptionParagraphs':sum(len(q['description']) for q in old.values()),
            'newMilestoneQuests':len(new)-len(old),'tutorialQuestNodes':len(new),'milestoneDependencyEdges':visible_deps,
            'freeReadingReferenceNodes':len(old),'optionalReferenceNodes':sum(new[key].get('optional') is True for key in old),
            'decorativeReferenceEdges':sum(len(d['quest_enhance_decorative_lines']) for d in documents.values()),
            'geometry':geometry(documents,outside_quests)}

def readme(report):
    lines=['# 机械动力建厂指引草稿','',
      '科技主线编排由 `tools/quest-workbench/build_create_progression.py` 维护；任务章节、图标与前置关系应与该生成器保持一致。',
      '', '本目录只生成草稿。正式接入由 `tools/quest-workbench/reorganize_create_progression.py` 备份、校验并同步；生成器不写任何正式任务根或manifest。',
      '', '`source-inventory.json` 是首次捕获的11章、164教程完整冻结基线，已存在时永不自动覆盖。安装删去7个旧章后，重跑仍从此基线生成，不会丢教程或重复追加阶段说明。',
      '', '四章为建厂主线、物流与仓储、农业与生产、铁路与运输。164张原卡保留quest/task IDs、任务结构、图标、奖励及原文段落；阶段定位与自由参考说明只添加在原文之前。',
      '', '新增22个建造验收均为手动checkmark、无奖励。主干9步，另有可选的早期SteamPowered站支路；物流/农业/铁路各4步。164参考卡全部optional，不计章节完成要求。实线串起验收流程；装饰辅助线仅把知识卡挂到实际使用阶段，不要求逐卡阅读。flexible允许提前记录进度，但验收节点仍需其真实dependencies满足后完成；不把flexible说成免除依赖。',
      '', '物流订单先于动力臂，只有动力臂验收额外依精密装配。农业从持续水力接出，物流从可停机工位接出，铁路从工业与装配备料接出，不锁Create蒸汽引擎。',
      '', '主线横向y=0，编号大卡；阶段参考用紧凑上下短列。可选蒸汽站从工业备料接出，不挡精密或铁路。三个专题与原有蒸汽/精智任务使用原生quest_links，保留原任务进度，不复制旧主线。',
      '', '## 建厂验收顺序','']
    lines += ['- '+m['title']+' (`'+m['id']+'`)' for m in report['mainline']]
    lines += ['', '## 验证与重建','', '```sh','python3 tools/quest-workbench/build_create_progression.py',
              'python3 tools/quest-workbench/build_create_progression.py --check','```','',
              '报告见 `report.json`。检测：164正文后缀/任务/图标/奖励保留、稳定ID无冲突、186节点、引用存在、依赖无环、原参考0硬门槛、0卡片重叠/0线交叉/0线穿非端点卡片（包含原生任务链接显示的依赖）。',
              '', '已核对配方事实：工作台粉碎轮；早期SteamPowered青铜站无需精密且须匹配飞轮；熔融黄铜合金并行路线；Vintage冲压/模具/注液的一轮精密装配；电子管直接路线；动力合成器/动力臂在精密后；包裹网络不整体锁精密；铁路接工业材料而非Create蒸汽引擎。']
    return '\n'.join(lines)+'\n'

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check',action='store_true',help='Validate and compare all generated bytes without writing')
    ap.add_argument('--output',type=Path,default=OUTPUT)
    args=ap.parse_args()
    output=args.output.resolve(); loads=parser(); data=baseline(output,loads,args.check)
    documents,mappings=generate(data); validation=validate(data,documents)
    report={'kind':'create-build-progression-draft-v1','group':GROUP,**validation,
            'chapters':[{'file':f,'id':d['id'],'title':d['title'],'quests':len(d['quests']),
                         'references':sum(q['id'] in {m['questId'] for m in mappings} for q in d['quests']),
                         'milestones':len(d['quests'])-sum(q['id'] in {m['questId'] for m in mappings} for q in d['quests']),
                         'links':len(d['quest_links'])} for f,d in documents.items()],
            'mainRoot':qid('factory','plan'),
            'mainline':[{'key':s['key'],'title':s['title'],'id':qid('factory',s['key'])} for s in milestones()['factory'] if s['key']!='steam'],
            'optionalBuildBranches':[{'key':'steam','id':qid('factory','steam'),'from':qid('factory','materials')}],
            'topicRoots':{c:qid(c,milestones()[c][0]['key']) for c in CHAPTERS if c!='factory'},
            'layout':{'direction':'left-to-right','mainlineY':0,'stageStep':7.5,'referenceSize':0.8,'milestoneSize':1.3,
                      'referenceColumnStep':1.9,'referenceRowStep':1.25},
            'referenceMapping':mappings,'frozenSourceHashes':data['sha256'],
            'retiredFiles':sorted(set(data['chapters'])-set(documents)),
            'policy':'Original references are free reading; only new build-acceptance milestones have dependencies. No rewards added.'}
    blobs={Path('chapters')/f:snbt(d)+'\n' for f,d in documents.items()}
    blobs.update({Path('chapter_groups.fragment.snbt'):snbt({'chapter_groups':[GROUP]})+'\n',
                  Path('report.json'):json.dumps(report,ensure_ascii=False,indent=2)+'\n',Path('README.md'):readme(report)})
    for relative,blob in blobs.items():
        if relative.suffix=='.snbt': loads(blob)
        path=output/relative
        if args.check:
            if not path.exists() or path.read_text()!=blob: raise ValueError(f'Outdated generated file: {path}')
        else:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_text(blob)
    if set(p.name for p in (output/'chapters').glob('*.snbt'))!=set(documents):raise ValueError('Unexpected extra draft chapter')
    print(json.dumps({'mode':'check' if args.check else 'generate',**validation,'root':report['mainRoot'],'output':str(output)},ensure_ascii=False))

if __name__=='__main__':main()
