#!/usr/bin/env python3
"""Generate one compact native-tree Bumblezone chapter; never deploy game files."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = PROJECT / 'design/bumblezone-quest-research/inventory.json'
DEFAULT_OUTPUT = PROJECT / 'design/bumblezone-quest-draft'
NAMESPACE = 'the_bumblezone:'
ID_SEED = 'cmi-expedition/bumblezone/1.20.1/v1/'
GROUP = {'id': '54D4CAA40ADB5408', 'title': '异境冒险'}
FILENAME = 'bumblezone_01_exploration.snbt'
CHAPTER_ID = '5BAAB2F63337EF1E'
TITLE = '蜜蜂领域'
LEGACY = {'bumblezone_02_queen.snbt': '94B407DE018F0D06', 'bumblezone_03_sanctum.snbt': '5D6D999BA7EB3886'}
SOURCE_ROOTS = [PROJECT / 'clients/cmi-expedition/instance/config/ftbquests/quests',
                PROJECT / 'clients/cmi-expedition/overlay/config/ftbquests/quests',
                PROJECT / 'servers/cmi-expedition/instance/config/ftbquests/quests']
LOGO = 'the_bumblezone:the_bumblezone_logo_large.png'
QUEEN_IMAGE = 'the_bumblezone:textures/entity_icon/bee_queen.png'
ESSENCE_IMAGE = 'the_bumblezone:textures/item/essence/essence_of_the_bees.png'
TEAM_NOTE = '玩法任务自动检测玩家已完成的原生进度。同队任一在线成员完成，可记入团队任务书；不会向其他队员授予原生进度、个人能力或女王资格。'
DISPLAY_NOTE = '画布按模组原生进度树从左向右展示。连线只表示原生展示关系，不是本任务书的完成前置；已完成的原生进度可以直接补认。'
QUEEN_NOTE = '任务书记录首次完成。女王重置会清除原生愿望与内部计数，已完成的FTB团队记录不会随之重置；重玩与领奖按女王原生流程进行。'

ICON_OVERRIDES = {'the_queens_desire/flooding_the_housing_market': 'minecraft:beehive', 'the_queens_desire/honey_drunk': 'minecraft:honey_bottle', 'the_queens_desire/pollen_fight': 'the_bumblezone:pollen_puff', 'the_queens_desire/the_crazy_florist': 'the_bumblezone:pollen_puff', 'the_queens_desire/poison_warfare': 'the_bumblezone:bee_stinger', 'the_queens_desire/back_in_action': 'the_bumblezone:bee_stinger', 'the_queens_desire/peak_inefficiency': 'the_bumblezone:stinger_spear', 'the_queens_desire/hungry_hungry_bees': 'the_bumblezone:sugar_water_bottle', 'the_queens_desire/love_bees': 'the_bumblezone:honey_bucket'}
ROYAL_PATHS = {'structures/enter_throne_pillar', 'honey_bucket/drink_royal_jelly_bottle', 'honey_bucket/obtain_royal_jelly_bucket', 'honey_bucket/royal_jelly_block_piston', 'windy_air/obtain_windy_air', 'tools/obtain_throne_honey_compass'}

class Raw(str):
    """A trusted native SNBT literal, already validated before output."""

def stable_id(kind, key):
    # FTB 2001.4.22 reads hex IDs with signed Long.parseLong, not parseUnsignedLong.
    number = int(hashlib.sha256((ID_SEED + kind + '/' + key).encode()).hexdigest()[:16], 16)
    return f'{max(2, number & 0x7FFFFFFFFFFFFFFF):016X}'

def native_node_map(chapter):
    """Identify installed quests by their gameplay target, never by a stale ID."""
    mapped = {}
    for node in chapter.get('quests', []):
        targets = [task.get('advancement') for task in node.get('tasks', [])
                   if task.get('type') == 'advancement' and task.get('criterion', '') == '']
        if len(targets) == 1:
            key = targets[0]
        elif any(LOGO in text for text in node.get('description', [])):
            key = NAMESPACE + 'root'
        elif any('github.com/TelepathicGrunt/Bumblezone/wiki' in text for text in node.get('description', [])):
            key = NAMESPACE + 'wiki'
        else:
            raise ValueError('Cannot identify an existing Bumblezone quest: ' + node.get('id', '?'))
        if key in mapped:
            raise ValueError('Duplicate installed native advancement: ' + key)
        mapped[key] = node
    return mapped

def snbt(value, depth=0):
    prefix = '\t' * depth
    child = '\t' * (depth + 1)
    if isinstance(value, Raw):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f'{value:.3f}'.rstrip('0').rstrip('.') + ('.0d' if value.is_integer() else 'd')
    if isinstance(value, list):
        if not value:
            return '[ ]'
        if len(value) <= 4 and all(isinstance(v, (str, int, bool)) for v in value):
            return '[' + ' '.join(snbt(v, depth) for v in value) + ']'
        return '[\n' + '\n'.join(child + snbt(v, depth + 1) for v in value) + '\n' + prefix + ']'
    if isinstance(value, dict):
        if not value:
            return '{ }'
        lines = []
        for key, item in value.items():
            rendered_key = key if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.+-]*', key) else snbt(key)
            lines.append(f'{child}{rendered_key}: {snbt(item, depth + 1)}')
        return '{\n' + '\n'.join(lines) + '\n' + prefix + '}'
    raise TypeError(f'Unsupported SNBT value {type(value)}')

def parser():
    path = PROJECT / 'clients/cmi-expedition/tools/ftb_snbt.py'
    spec = importlib.util.spec_from_file_location('bumblezone_ftb_snbt', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.loads

def native_icon(advancement, loads):
    override = ICON_OVERRIDES.get(short_id(advancement))
    if override:
        return override
    native = advancement['source']['display']['icon']
    item = native['item']
    if 'nbt' not in native:
        return item
    loads(native['nbt'])
    return {'Count': Raw('1b'), 'id': item, 'tag': Raw(native['nbt'])}

def image(resource, x, y, width, height, hover='', alpha=1.0):
    return {'image': resource, 'x': float(x), 'y': float(y), 'width': float(width),
            'height': float(height), 'rotation': 0.0, 'alpha': round(alpha * 255), 'order': -1,
            'hover': [hover] if hover else []}

def short_id(advancement):
    return advancement['id'].split(':', 1)[1]

def all_nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from all_nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_nodes(child)

def old_kind(row):
    path = short_id(row)
    if path.startswith('the_queens_desire/') or path in ROYAL_PATHS:
        return 'queen'
    if path.startswith('essence/') or path == 'structures/enter_sempiternal_sanctum':
        return 'sanctum'
    return 'exploration'


def make_node(row, loads):
    path = short_id(row)
    guide = path in {'root', 'wiki'}
    title = row['title_zh'].replace('一家飞机', '一架飞机')
    if guide:
        if path == 'root':
            title = '蜜蜂领域'
            description = [
                '{image:the_bumblezone:the_bumblezone_logo_large.png width:180 height:67 align:center}',
                '从蜂巢启程，探索蜂蜜海洋、遗迹与女王的王座。留好返程的位置，小心激怒蜂群。',
                '向蜂巢投掷末影珍珠，或借助活塞进入蜜蜂领域，任选一种方式即可。',
                '与女王完成首次交易后，可同时实现她的16项愿望。全部完成后，再去见女王领取奖励。',
                '亲自食用蜜蜂精华，获得进入圣所挑战的资格。六种颜色的挑战可以自由选择先后。',
            ]
        else:
            title = '蜜蜂领域手册'
            description = ['想了解蜂群、女王与圣所的更多秘密，可以查阅蜜蜂领域手册。',
                           'https://github.com/TelepathicGrunt/Bumblezone/wiki',
                           'https://www.mcmod.cn/class/2489.html']
        task = {'id': stable_id('guide-task', row['id']), 'type': 'checkmark', 'title': '已阅读'}
        node_id = stable_id('guide', row['id'])
    else:
        description = [row['description_zh']]
        if path == 'the_queens_desire/the_crazy_florist':
            description = ['用花粉球授粉，让花朵累计盛开8次。']
        if path.startswith('the_queens_desire/'):
            description += ['先与女王完成首次交易，之后可以同时实现她的16项愿望。']
        if path == 'the_queens_desire/the_beginning':
            description.insert(0, '{image:the_bumblezone:textures/entity_icon/bee_queen.png width:64 height:64 align:center}')
            description += ['与女王完成首次交易，听听她的愿望。全部16项愿望完成后，回来领取蜜蜂精华。']
        if path == 'the_queens_desire/journeys_end':
            description += ['完成全部16项愿望后，右键女王领取最终奖励。']
        if path == 'essence/bee_essence_infusion':
            description.insert(0, '{image:the_bumblezone:textures/item/essence/essence_of_the_bees.png width:48 height:48 align:center}')
            description += ['从女王处领取蜜蜂精华，并亲自食用，获得挑战圣所的资格。每位冒险者都需要亲自食用。']
        if path == 'structures/enter_sempiternal_sanctum' or path.startswith('essence/essence_'):
            description += ['六种颜色的挑战可以自由选择先后。亲自进入挑战，赢得属于你的精华。']
        if path in {'teleportation/teleport_to_bumblezone_pearl', 'teleportation/teleport_to_bumblezone_piston'}:
            description += ['珍珠与活塞都能带你进入蜜蜂领域，任选一种方式即可。']
        task = {'id': stable_id('task', row['id']), 'type': 'advancement', 'advancement': row['id'], 'criterion': ''}
        node_id = stable_id('quest', row['id'])
    return {'id': node_id, 'title': title, 'icon': native_icon(row, loads),
            'description': description, 'shape': 'rsquare' if guide else ('hexagon' if row['source']['display'].get('frame') == 'challenge' else 'circle'),
            'size': 1.0, 'tasks': [task], 'rewards': [], 'x': 0.0, 'y': 0.0}


def compact_tree(rows, x_step=2.0, y_step=1.25):
    "Contour-compacted ordered tree, left to right, no extra branch/module spacing."
    by_id = {row['id']: row for row in rows}
    children = {key: [] for key in by_id}
    roots = []
    for row in rows:
        parent = row['source'].get('parent')
        if parent:
            if parent not in children:
                raise ValueError('Native parent missing: ' + parent)
            children[parent].append(row['id'])
        else:
            roots.append(row['id'])
    if roots != [NAMESPACE + 'root']:
        raise ValueError('Expected exactly one native root')
    active = set()
    def bounds(positions):
        contours = {}
        for depth, y in positions.values():
            low, high = contours.get(depth, (math.inf, -math.inf))
            contours[depth] = (min(low, y), max(high, y))
        return contours

    def visit(key):
        if key in active:
            raise ValueError('Native advancement parent cycle')
        active.add(key)
        packed = {}
        roots_y = []
        contour = {}
        for child in children[key]:
            branch = visit(child)
            child_contour = bounds(branch)
            shift = max((contour[d][1] - lo + y_step for d, (lo, _) in child_contour.items() if d in contour), default=0.0)
            moved = {name: (depth, y + shift) for name, (depth, y) in branch.items()}
            roots_y.append(moved[child][1])
            packed.update(moved)
            contour = bounds(packed)
        center = (roots_y[0] + roots_y[-1]) / 2 if roots_y else 0.0
        positioned = {name: (depth + 1, y - center) for name, (depth, y) in packed.items()}
        positioned[key] = (0, 0.0)
        active.remove(key)
        return positioned
    raw = visit(roots[0])
    if len(raw) != len(rows):
        raise ValueError('Native advancement tree is disconnected')
    return {key: (depth * x_step, y) for key, (depth, y) in raw.items()}, children


def decorative_ref(identifier):
    return 'q:' + format(int(identifier, 16), 'x')


def place_decoration(resource, anchor, nodes, width, height, preferred_sign=-1):
    "Keep small illustrations near their native branch without covering quests."
    for distance in [2.4, 3.0, 3.6, 4.2, 4.8, 5.4]:
        for sign in [preferred_sign, -preferred_sign]:
            for dx in [0.0, 1.0, -1.0]:
                x, y = anchor['x'] + dx, anchor['y'] + sign * distance
                if all(abs(x - node['x']) >= width / 2 + 1.0 or abs(y - node['y']) >= height / 2 + 0.65 for node in nodes):
                    return image(resource, x, y, width, height)
    raise ValueError('Cannot place a decoration without covering native nodes')


def crossing_count(nodes, lines):
    coordinates = {node['id']: (node['x'], node['y']) for node in nodes}
    edges = [(f'{int(line["nodes"][0][2:],16):016X}', f'{int(line["nodes"][1][2:],16):016X}') for line in lines]
    def orientation(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])
    count = 0
    for index, (a, b) in enumerate(edges):
        p, q = coordinates[a], coordinates[b]
        for c, d in edges[index + 1:]:
            if len({a,b,c,d}) < 4:
                continue
            r, s = coordinates[c], coordinates[d]
            if orientation(p,q,r)*orientation(p,q,s) < -1e-8 and orientation(r,s,p)*orientation(r,s,q) < -1e-8:
                count += 1
    return count


def line_hits_icon(a, b, node, margin=0.02):
    """Open segment versus a non-endpoint's square icon bounds, with clearance."""
    radius = float(node.get('size', 1.0)) / 2 + margin
    lower, upper = 0.0, 1.0
    for axis in ['x', 'y']:
        start = a[axis]
        delta = b[axis] - start
        minimum, maximum = node[axis] - radius, node[axis] + radius
        if abs(delta) < 1e-10:
            if not minimum < start < maximum:
                return False
            continue
        near, far = sorted(((minimum-start)/delta, (maximum-start)/delta))
        lower, upper = max(lower, near), min(upper, far)
        if upper-lower <= 1e-9:
            return False
    return upper > 1e-9 and lower < 1-1e-9


def icon_crossings(nodes, native_pairs):
    return [(parent, child, key) for parent, child in native_pairs
            for key, node in nodes.items() if key not in (parent, child)
            and line_hits_icon(nodes[parent], nodes[child], node)]


def node_boxes_overlap(nodes):
    values = list(nodes.values())
    for index, a in enumerate(values):
        for b in values[index+1:]:
            if abs(a['x']-b['x']) < 1.9 and abs(a['y']-b['y']) < 1.25-1e-8:
                return True
    return False


def clear_local_icon_crossings(nodes, children, native_pairs, lines):
    """Nudge only an offending terminal branch; keep every native depth/x fixed."""
    adjustments = []
    for _ in range(16):
        hits = icon_crossings(nodes, native_pairs)
        if not hits:
            return adjustments
        parent, child, blocker = hits[0]
        def subtree(key):
            yield key
            for descendant in children[key]:
                yield from subtree(descendant)
        affected = list(subtree(child))
        baseline = {key:nodes[key]['y'] for key in affected}
        direction = -1 if nodes[child]['y'] < nodes[blocker]['y'] else 1
        for step in range(1, 25):
            shift = direction * step * 0.125
            for key, y in baseline.items():
                nodes[key]['y'] = y + shift
            if not node_boxes_overlap(nodes) and not crossing_count(list(nodes.values()), lines) and len(icon_crossings(nodes,native_pairs)) < len(hits):
                adjustments.append({'nativeBranchRoot':child, 'offsetY':shift, 'movedNodes':len(affected),
                                    'blockedEdge':[parent,child], 'avoidedNode':blocker})
                break
        else:
            for key,y in baseline.items():
                nodes[key]['y'] = y
            raise ValueError('Unable to clear a native connector with a small local y adjustment')
    raise ValueError('Native icon-clearance repair did not converge')


def generate(inventory_path):
    raw = inventory_path.read_bytes()
    inventory = json.loads(raw)
    rows = inventory['advancements']
    by_id = {row['id']: row for row in rows}
    gameplay = [row for row in rows if short_id(row) not in {'root', 'wiki'}]
    if len(rows) != 133 or len(gameplay) != 131 or len(by_id) != 133:
        raise ValueError('Expected installed native inventory133 / gameplay131')
    loads = parser()
    receipt = json.loads((PROJECT/'tools/quest-workbench/data/active-export.json').read_text())
    export_root = Path(receipt['exportRoot'])
    catalog_path = export_root/'items.json'
    catalog_raw = catalog_path.read_bytes()
    catalog = json.loads(catalog_raw)
    catalog = catalog.get('items', []) if isinstance(catalog,dict) else catalog
    catalog_by_id = {row['id']: row for row in catalog}
    for item in set(ICON_OVERRIDES.values()):
        entry = catalog_by_id.get(item)
        if not entry or not entry.get('icon') or not (export_root/entry['icon']).is_file():
            raise ValueError('Unverified related-item icon: '+item)
    nodes = {row['id']: make_node(row,loads) for row in rows}
    installed_path = SOURCE_ROOTS[0] / 'chapters' / FILENAME
    installed = loads(installed_path.read_text()) if installed_path.exists() else None
    installed_nodes = native_node_map(installed) if installed else None
    if installed_nodes is not None:
        if set(installed_nodes) != set(nodes):
            raise ValueError('Installed native quest set differs; refusing to replace progress identities')
        for key, fresh in list(nodes.items()):
            # A running FTB instance may already have repaired invalid old IDs.
            # Keep its entire identity/detection/layout, and refresh player prose only.
            current = dict(installed_nodes[key])
            current.update(title=fresh['title'], description=fresh['description'])
            current.setdefault('rewards', [])
            nodes[key] = current
    coordinates, children = compact_tree(rows)
    for key, (x,y) in coordinates.items():
        nodes[key].update(x=x,y=y)
    lines = [{'nodes':[decorative_ref(nodes[row['source']['parent']]['id']),decorative_ref(nodes[row['id']]['id'])]}
             for row in rows if row['source'].get('parent')]
    native_pairs = [(row['source']['parent'],row['id']) for row in rows if row['source'].get('parent')]
    clearance_adjustments = clear_local_icon_crossings(nodes,children,native_pairs,lines)
    coordinates = {key:(node['x'],node['y']) for key,node in nodes.items()}
    chapter = {'id':CHAPTER_ID,'filename':FILENAME.removesuffix('.snbt'),'title':TITLE,
               'group':installed.get('group', '') if installed else GROUP['id'],
               'icon':'the_bumblezone:honey_compass','order_index':installed.get('order_index', 100) if installed else 100,
               'progression_mode':'flexible','consume_items':False,
               'default_hide_dependency_lines':False,'default_quest_shape':'circle',
               'images':[], 'quests':[nodes[row['id']] for row in rows], 'quest_links':[],
               'quest_enhance_decorative_lines':lines}
    chapter['images'] = [
        place_decoration(LOGO, {'x':3.0,'y':nodes[NAMESPACE+'root']['y']}, chapter['quests'],6.0,2.22,-1),
        place_decoration(QUEEN_IMAGE,nodes[NAMESPACE+'the_queens_desire/the_beginning'],chapter['quests'],1.6,1.6,1),
        place_decoration(ESSENCE_IMAGE,nodes[NAMESPACE+'essence/bee_essence_infusion'],chapter['quests'],1.2,1.2,-1),
    ]
    ids = [CHAPTER_ID]+([chapter['group']] if chapter['group'] else [])+[node['id'] for node in nodes.values()]+[task['id'] for node in nodes.values() for task in node['tasks']]
    if len(ids) != len(set(ids)) or not all(re.fullmatch('[0-9A-F]{16}',key) and 1 < int(key,16) <= 0x7FFFFFFFFFFFFFFF for key in ids):
        raise ValueError('Generated ID collision or invalid identifier')
    if len(lines) != 132 or any(node.get('dependencies') for node in nodes.values()):
        raise ValueError('Native tree must have132 display edges and0 extra FTB dependencies')
    assert Counter(task['advancement'] for node in nodes.values() for task in node['tasks'] if task['type']=='advancement') == Counter(row['id'] for row in gameplay)
    for node in nodes.values():
        assert not node['rewards']
        for task in node['tasks']:
            if task['type']=='advancement': assert task['criterion']==''
    id_set = set(ids)
    legacy_ids = {name:{identifier} for name,identifier in LEGACY.items()}
    for row in rows:
        kind = old_kind(row)
        name = 'bumblezone_02_queen.snbt' if kind=='queen' else 'bumblezone_03_sanctum.snbt' if kind=='sanctum' else None
        if name: legacy_ids[name].update([nodes[row['id']]['id'],nodes[row['id']]['tasks'][0]['id']])
    for root in SOURCE_ROOTS:
        for path in root.rglob('*.snbt') if root.exists() else []:
            relative = path.relative_to(root).as_posix()
            allowed = id_set if relative=='chapters/'+FILENAME else legacy_ids.get(path.name,set()) if relative=='chapters/'+path.name else set()
            for node in all_nodes(loads(path.read_text())):
                existing = node.get('id')
                if existing not in id_set or existing in allowed:
                    continue
                if relative=='chapter_groups.snbt' and existing==GROUP['id'] and node.get('title')==GROUP['title']:
                    continue
                raise ValueError(f'New ID collides with unrelated content: {path}: {existing}')
    if node_boxes_overlap(nodes):
        raise ValueError('Native-tree node bounding boxes overlap or violate1.25 minimum y spacing')
    node_ids = {node['id'] for node in nodes.values()}
    for line in lines:
        assert all(reference==decorative_ref(f'{int(reference[2:],16):016X}') and f'{int(reference[2:],16):016X}' in node_ids for reference in line['nodes'])
    crossings = crossing_count(chapter['quests'],lines)
    if crossings: raise ValueError('Native-tree drawing has edge crossings')
    node_crossings = icon_crossings(nodes,native_pairs)
    if node_crossings: raise ValueError('Native-tree connector crosses a non-endpoint icon')
    resources = {entry['image'] for entry in chapter['images']}
    for node in nodes.values():
        for text in node['description']: resources.update(re.findall(r'\{image:([^\s}]+)',text))
    if not resources <= {row['resource'] for row in inventory['png_assets']}:
        raise ValueError('Native resource absent from inventory')
    jar = PROJECT/next(row['path'] for row in inventory['mods'] if row['path'].startswith('clients/') and 'the_bumblezone-' in row['path'])
    with zipfile.ZipFile(jar) as archive:
        for row in rows:
            if json.loads(archive.read(row['jar_path'])) != row['source']:
                raise ValueError('Installed advancement differs from research inventory')
    stats = {'filename':FILENAME,'id':CHAPTER_ID,'title':TITLE,'quests':133,'advancementTasks':131,
             'guideTasks':2,'images':3,'canvasTexts':0,'branchEdges':0,'recommendedEdges':132,'rewards':0}
    report = {
        'format':2,'target':'Minecraft1.20.1 Forge / FTB Quests2001.4.22 / Bumblezone7.14.0',
        'sourceInventory':str(inventory_path.relative_to(PROJECT)), 'sourceInventorySha256':hashlib.sha256(raw).hexdigest(),
        'group':GROUP,'chapters':[stats],'gameplayAdvancements':131,'guideNodes':2,'totalQuests':133,
        'allGameplayTaskType':'advancement','allGameplayCriterion':'','allFtbRewards':0,'duplicateEssenceRewards':0,
        'branchEdges':{'native_tree':0},'recommendedEdges':{'native_tree':132},'nativeParentEdges':132,
        'singleChapter':True,'legacyChaptersToRemove':[{'filename':name,'id':key} for name,key in LEGACY.items()],
        'layout':{'direction':'left-to-right','algorithm':'native-depth contour-compacted ordered tree',
                  'xStep':2.0,'minimumSiblingYStep':1.25,'nodeSize':1.0,'maxDepth':max(round(x/2.0) for x,y in coordinates.values()),
                  'bounds':{'minX':min(x for x,y in coordinates.values()),'maxX':max(x for x,y in coordinates.values()),
                            'minY':min(y for x,y in coordinates.values()),'maxY':max(y for x,y in coordinates.values())},
                  'edgeCrossings':crossings,'moduleTitles':0},
        'iconClearance':{'nonEndpointNodeCrossings':len(node_crossings),'iconBounds':'square size/2 plus0.02 grid margin',
                         'localYAdjustments':clearance_adjustments,'xDepthAndStepUnchanged':True},
        'displayPolicy':DISPLAY_NOTE,'realDependencyPolicy':'No additional FTB prerequisites. Native criteria remain authoritative, including Queen first trade/all16 and personal essence qualification. Root/wiki checkmarks never gate gameplay.',
        'nativeResources':sorted(resources),
        'coverage':[{'advancement':row['id'],'chapter':FILENAME.removesuffix('.snbt'),'questId':nodes[row['id']]['id'],
                     'taskId':nodes[row['id']]['tasks'][0]['id'],'nativeParent':row['source'].get('parent'),
                     'nativeIconItem':row['source']['display']['icon']['item'],
                     'iconItem':ICON_OVERRIDES.get(short_id(row),row['source']['display']['icon']['item'])} for row in gameplay],
        'nodeMapping':[{'nativeId':row['id'],'questId':nodes[row['id']]['id'],'taskId':nodes[row['id']]['tasks'][0]['id'],
                        'x':nodes[row['id']]['x'],'y':nodes[row['id']]['y'],'parent':row['source'].get('parent')} for row in rows],
        'iconCatalogEvidence':{'path':str(catalog_path.relative_to(PROJECT)),'sha256':hashlib.sha256(catalog_raw).hexdigest()},
        'iconOverrides':[{'advancement':NAMESPACE+path,'nativeIcon':by_id[NAMESPACE+path]['source']['display']['icon'],
                          'overrideItem':item,'catalogName':catalog_by_id[item].get('n'),'catalogIcon':catalog_by_id[item]['icon']} for path,item in ICON_OVERRIDES.items()],
        'checks':['133 native nodes and132 original parent edges exactly matched','131 gameplay advancement tasks exactly once',
                  '0 extra FTB dependencies,0 rewards','Stable existing133 quest/task IDs retained',
                  'Unrelated formal IDs cannot collide; old02/03 IDs allowed only for migration of their own objects',
                  'No node bounding-box overlaps;0 edge crossings;0 connectors through non-endpoint icon bounds',
                  'All native images exist;9 icon overrides catalog-verified',
                  'Every decorative reference same-chapter lowercase unsigned hex without leading zero'],
        'runtimeValidation':'Static generation verified. Native advancement completion, team semantics, Queen resets and in-game native-texture rendering still require a test-copy check.',
    }
    files={'chapters/'+FILENAME:snbt(chapter)+'\n','chapter_groups.fragment.snbt':snbt({'chapter_groups':[GROUP]})+'\n',
           'report.json':json.dumps(report,ensure_ascii=False,indent=2)+'\n','README.md':make_readme(report)}
    for name,text in files.items():
        if name.endswith('.snbt'):loads(text)
    return files,report


def make_readme(report):
    return f'''# 蜜蜂领域 · 单章原生进度树草稿

当前Minecraft1.20.1、Bumblezone7.14.0、FTB Quests2001.4.22。最终只保留一个蜜蜂维度内容章：`chapters/{FILENAME}`，章ID仍为`{CHAPTER_ID}`，分组仍为“{GROUP['title']}”/`{GROUP['id']}`。

本生成器只写草稿。正式迁移由独立安装步骤备份后执行，状态见`tools/quest-workbench/evidence/bumblezone-integration/install.json`。安装时需要删除旧`bumblezone_02_queen.snbt`、`bumblezone_03_sanctum.snbt`，保留其他章节和已有分组。

131项玩法自动检测任务加root/wiki两个阅读节点，共133节点，保留原来的全部quest ID、task ID、检测对象、物品图标和零奖励规则；只是将原三个章节的任务放到同一章。两个阅读节点仍可手动勾选，但不会锁住玩法。

按已安装JAR的原生parent树原样连接132条父子边，从左向右按深度紧凑排布；轮廓压缩算法让不同分支在不重叠的前提下贴近，不再做六模块网格或四列女王模块。统一节点size1、横步2格、同层最小纵步1.25格。对长斜线擦过相邻图标的位置只做局部分支纵向微调，不增加横向空隙。图面无节点重叠、无边交叉、无线段穿过非端点图标（按图标正方形边界加0.02格余量检查）。清掉11个主题文字模块标题，只保留3处原生logo/女王/精华点缀。

**原生parent只控制展示。** 所有132条线均使用Quest Enhance装饰线，额外FTB dependencies为0。连线不延迟已有原生进度完成，也不要求先勾说明节点。珍珠/活塞仍是替代入口；女王16愿望在原生首次交易后可并行；六精华的原生展示链也不是任务书逐色硬门槛。真实资格和女王终点16项AND条件都由原生advancement检测负责。

同队共享FTB完成记录，不授予其他队员个人精华资格。女王重置不清已完成的FTB记录，无法恢复安装前已被清除的历史。所有奖励仍由模组原生流程发放。

图标保持已审核版本，9项女王工艺图标继续便于查配方；任务本体仍为advancement。当前导出catalog中对应7种物品及图标已核实。所有图片直接引用已安装模组资源，不提取重发贴图。

```sh
python3 tools/quest-workbench/import_bumblezone.py
python3 tools/quest-workbench/import_bumblezone.py --check
```

`report.json`包含单章信息、133节点稳定ID映射、132条native parent覆盖、坐标与压缩布局统计、旧两章删除清单和静态核验。现有其他内容不由此生成器修改。
'''


def main():
    command=argparse.ArgumentParser(description=__doc__)
    command.add_argument('--inventory',type=Path,default=DEFAULT_INVENTORY)
    command.add_argument('--output',type=Path,default=DEFAULT_OUTPUT)
    command.add_argument('--check',action='store_true')
    args=command.parse_args()
    output=args.output.resolve()
    for root in SOURCE_ROOTS:
        if output==root.resolve() or root.resolve() in output.parents or output in root.resolve().parents:
            raise ValueError('Generator cannot write to or around a formal quests root')
    files,report=generate(args.inventory.resolve())
    if args.check:
        mismatches=[name for name,text in files.items() if not (output/name).is_file() or (output/name).read_text()!=text]
        mismatches += ['chapters/'+name for name in LEGACY if (output/'chapters'/name).exists()]
        if mismatches: raise ValueError('Draft differs or contains obsolete chapters: '+', '.join(mismatches))
    else:
        for name,text in files.items():
            path=output/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        for name in LEGACY:
            (output/'chapters'/name).unlink(missing_ok=True)
    print(json.dumps({'mode':'checked' if args.check else 'generated','output':str(output),'chapters':report['chapters'],
                      'layout':report['layout'],'legacyChaptersToRemove':report['legacyChaptersToRemove']},ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
