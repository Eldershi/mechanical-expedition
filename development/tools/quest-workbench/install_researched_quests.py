#!/usr/bin/env python3
"""Stage recipe-reviewed research as additive FTB chapters; apply is explicit.

Never edits existing chapters, chapter groups, recipes, rewards or player data.
Decorative relationships preserve recipe alternatives without imposing FTB locks.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import secrets
import zipfile
from research_horizontal_layout import anchor_key, horizontal_layout

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'design/researched-quest-integration-20261018/staging'
PIPELINES = [('adventure', 'video-quest-pipeline-20261018'), ('technology', 'tech-video-quest-pipeline-20261018')]
INSTANCE_ROOTS = ['clients/cmi-expedition/instance', 'clients/cmi-expedition/overlay', 'servers/cmi-expedition/instance']
HEX = re.compile(r'[0-9a-fA-F]{16}\Z')
RESOURCE = re.compile(r'[a-z0-9_.-]+:[a-z0-9_./-]+\Z')
NAMESPACE = 'expedition_research'
MODAL = re.compile(r'FTB|JSON|快照|源码|代码|脚本|校验|审计|复读|转写|视频|预览|草稿|候选|待核|未验证|已验证|已证实|本批|本轮|本次|sourceId|catalogKey|recipeVariants|recipeCondition|[Cc]heckmark|[Ww][Ii][Pp]|任务书.*检测|物品检测|背包检测|检测建议|实现状态')
META_SENTENCE = re.compile(r'FTB|JSON|快照|源码|代码|脚本|校验|审计|复读|转写|视频|预览|草稿|候选|待核|未验证|已验证|已证实|本批|本轮|sourceId|catalogKey|recipeVariants|recipeCondition|[Cc]heckmark|[Ww][Ii][Pp]|未核|已核|placed_feature|来源/操作条件见|本步骤正文|本次|旧版|旧片|版本|未运行|未进行|未启动|不能冒充|不冒充|不宣称|不声称|不能宣称|不能据此|不据|不要求.*任务|不.*写成|另.*验收|任务端点|云占位|逐字节|哈希|客户端|服务端|生存实测|未实测|需实测|需.*核验|需.*验证|须.*验证|按实际.*验证|物品检测|背包检测|任务书.*检测|检测建议|检测实现|后台检测|本组|本项|本期|阅读节点|硬边|硬前置|highPriorityData|type=|该ID|criteria|元数据|未知留null|正式检测|登记配方|保留参考|精魂数据|不造|源码|数据表|未完成.*(?:内容|维度)|正式.*任务|新增流程说明|材料任务|任务资格|作为任务|写入任务|任务门槛|给.*设.*门槛|题中|默认.*Values|另列证据|数组|未在生存验证|本期终点|造终焉|电话本|核实来源|完成通过|按机制取得/验证|全邪术已解锁|不要额外设置|不能.*任务|不是.*资格')
REPLACEMENT_PATH=ROOT/'design/researched-quest-integration-20261018/root-review/player-sentence-replacements.json'
PLAYER_REPLACEMENTS=json.loads(REPLACEMENT_PATH.read_text()) if REPLACEMENT_PATH.exists() else {}
PLAYER_REPLACEMENTS.update({'选用焦炉煤炭配方。本任务不排除热解炉、旋转窑及其他路线。':'使用焦炉的煤炭配方，也可按需要选择其他焦化路线。','从配方查询核对配方。本任务只检测取得。':'按配方制作发电机，为后续设备准备能源。','成品输出，模具保留或损耗情况按真实机制核验。':'加工后取出成品，保留可继续使用的模具。'})

def player_replacements(text):
    for before,after in sorted(PLAYER_REPLACEMENTS.items(),key=lambda pair:len(pair[0]),reverse=True):text=text.replace(before,after)
    return text.strip()

DISPLAY_NAMES = {'forge:raw_materials/uranium':'粗铀矿','minecraft:end/kill_dragon':'击败末影龙','eternal_starlight:starlight':'永恒星光','aether:enchanting':'祭坛加工','aether:freezing':'冰冻器加工','minecraft:ancient_city':'远古城市','hostilenetworks:warden':'监守者模型','deeperdarker:otherside':'幽冥','forge:fermentable':'可发酵原料','forge:oxygen':'氧气','hostilenetworks:zombie':'僵尸模型'}
REUSE_OPERATIONS = {'technology/A-tech-core-logic':'6A3204F0275C1DEA','technology/B-engblocks':'5486A9D8E0073EAB','technology/B-diode':'7986071E20EEF73C','technology/B-electronic':'6E87F1A6C2A966BD','technology/B-autowork':'6ED98C2148C69BD7','technology/B-squeezer':'6ED3E5867F2A90AB'}
DEFAULT_EDGE_EXCLUSIONS={'adventure/A-edge-aab7d98957ff','adventure/C-edge-264d69753077b5','adventure/C-edge-ed9299f5bad5ec'}
DEFAULT_NODE_PATCHES = {
    'adventure/A-ac-entry': {'title':'启程探索Alex洞穴','target':{'kind':'build_check','id':None},'conditions':['准备照明、补给和返程标记。'],'actions':['在主世界地下寻找目标洞穴群系，找到后记录入口和返程坐标，再展开对应支线。若另外取得带群系信息的洞穴石板，可选走勘探台解码与地图导航。'],'outcomes':['找到任意一个目标洞穴群系并留下返程标记。'],'nextSteps':['选择磁场洞穴、原始洞穴、渊海陷窟、毒化洞穴或异寂空谷继续探索。']},
    'adventure/A-es-eye': {'title':'从寻觅者取得寻觅之眼','optional':True,'conditions':['在永恒星光寻找自然出现的寻觅者。'],'actions':['击败寻觅者取得寻觅之眼；也可以直接探索遗迹。配合石板寻找诅咒花园或傀儡锻造厂，两处遗迹分别探索。'],'outcomes':['取得可用于定位遗迹的寻觅之眼。'],'nextSteps':[],'recipeFigures':[],'recipeImages':[],'assetIds':['A-asset-5ea1d202569d9b']},
    'adventure/C-item-enigmaticlegacy-cursed_ring': {'title':'了解七咒与灵魂回收','target':{'kind':'build_check','id':None},'conditions':[],'actions':['检查饰品栏中佩戴的七咒之戒、生命与护甲状态，准备灵魂水晶和死亡后的回收路线。七咒之戒会自动佩戴且无法取下；仍可正常睡眠。无需主动死亡或尝试卸戒。'],'outcomes':['查看自己的诅咒状态，并准备可靠的回收路线。'],'nextSteps':['按配装需要选择神秘遗物分支。']},
    'adventure/B.forbidden_arcanus.forge':{'target':{'kind':'build_check','id':None},'outcomes':['在现场完成赫菲斯托斯锻炉的转化，并打开锻炉界面。']},'adventure/B.forbidden_arcanus.aureal':{'target':{'kind':'build_check','id':None},'outcomes':['完成神秘水晶方尖碑的转化，使锻炉持续获得辉光。']},
    'adventure/B.forbidden_arcanus.tier2':{'target':{'kind':'build_check','id':None},'outcomes':['在锻炉界面确认等级由一阶升至二阶。']},
    'adventure/B.forbidden_arcanus.tier3':{'target':{'kind':'build_check','id':None},'outcomes':['在锻炉界面确认等级由二阶升至三阶。']},
    'adventure/B.forbidden_arcanus.higher':{'title':'按需要继续升级锻炉','target':{'kind':'build_check','id':None},'optional':True,'conditions':['先选择要进行的锻炉仪式，再查看它所需的锻炉等级。'],'actions':['若所选仪式需要四阶，将锻炉升级至四阶；需要五阶时再继续升级。四阶升级使用陨星碎片与符文，五阶涉及幽匿催发体、暗黑下界之星和龙鳞。按配方准备精华并启动升级。'],'outcomes':['锻炉界面达到所选仪式需要的等级。'],'nextSteps':['进行自己选定的仪式。']},
    'adventure/A-ac-decode':{'optional':True,'operationCheck':True}, 'adventure/A-ac-map':{'optional':True},'adventure/A-ac-magnets':{'operationCheck':True},'adventure/A-dd-transmitter':{'operationCheck':True},'adventure/A-es-ether':{'operationCheck':True},
}
SPEC = importlib.util.spec_from_file_location('research_snbt', ROOT / 'clients/cmi-expedition/tools/ftb_snbt.py')
SNBT = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(SNBT)


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(blob): return hashlib.sha256(blob).hexdigest() if blob is not None else None


def json_bytes(value): return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def ident(kind, key):
    n = int(hashlib.sha256(('expedition/researched-quests/20261018/v1/' + kind + '/' + key).encode()).hexdigest()[:16], 16) & 0x7fffffffffffffff
    return f'{max(n, 2):016X}'


def signed_id(key): return isinstance(key, str) and bool(HEX.fullmatch(key)) and 1 < int(key, 16) <= 0x7fffffffffffffff


def snbt(value, depth=0):
    tab, child = '\t' * depth, '\t' * (depth + 1)
    if isinstance(value, str): return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool): return 'true' if value else 'false'
    if isinstance(value, int): return str(value)
    if isinstance(value, float): return repr(value) + 'd'
    if isinstance(value, list):
        if not value: return '[ ]'
        return '[\n' + '\n'.join(child + snbt(v, depth + 1) for v in value) + '\n' + tab + ']'
    if isinstance(value, dict):
        if not value: return '{ }'
        return '{\n' + '\n'.join(child + (k if re.fullmatch(r'[\w.+-]+', k) else snbt(k)) + ': ' + snbt(v, depth + 1) for k, v in value.items()) + '\n' + tab + '}'
    raise TypeError(type(value))


def walk(value):
    if isinstance(value, dict):
        yield value
        for v in value.values(): yield from walk(v)
    elif isinstance(value, list):
        for v in value: yield from walk(v)


def read_safe(path):
    require(not path.is_symlink(), f'Refusing symlink file: {path}')
    return path.read_bytes() if path.exists() else None


def atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.' + secrets.token_hex(5) + '.tmp')
    try:
        tmp.write_bytes(blob); tmp.replace(path)
    finally: tmp.unlink(missing_ok=True)


def native_advancement_matches(task, resource):
    return task.get('type') == 'advancement' and task.get('advancement') == resource and task.get('criterion', '') == ''


def chapter_documents(root):
    result = {}
    for path in sorted((root / 'config/ftbquests/quests/chapters').glob('*.snbt')):
        result[path.name] = SNBT.loads(path.read_text())
    return result


def clean_text(text):
    text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', str(text))
    text = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text).replace('**', '').replace('`', '')
    text = text.replace('sim_cost=128FE/t','每 tick 消耗 128 FE').replace('energy=76800','消耗 76800 FE').replace('模型NBT为','模型绑定为').replace('NBT=','绑定为').replace('模型系统只是引用，不在此重写科技教程','').replace('允许击杀升级的配置已开启','通过击杀可以训练模型').replace('现装','')
    text = text.replace('经验收集','经验补给').replace('本图选水冷','选择水冷时').replace('现装指南','使用指南').replace('现装结构成型信息','多方块结构指南').replace('现装多方块图','多方块结构图').replace('现装Giselle有对应条件配方','按Giselle附属的配方制作模块').replace('channels配置为default，','').replace('现装1.20附属已含矩阵：','样板矩阵：').replace('材料按此节点的配方查询独立槽位准备','按配方图的各个材料槽独立备料').replace('读取MultiBlock.js','').replace('按highPriorityData登记配方装配，输出4二极管','使用部件装配机加工这些材料，得到4个激光二极管').replace('选immersiveengineering:blueprint/component_electronic；按当前type=thermal_extra:component_assembly运行','使用部件装配机加工这些材料，得到2个电子元件').replace('正确NBT蓝图','正确的工程蓝图').replace('所得与下一步：','').replace('读取遭遇节点','了解首领的唤醒方式').replace('阅读遭遇节点','了解首领的唤醒方式').replace('按任务材料及结构备料','按配方和结构备料').replace('自然生成证据为','在').replace('所得与下一步：','').replace('材料用途/加工去向（仅所选配方）：','').replace('本组补','补充').replace('A组','').replace('C组','').replace('9×9仅在已满足实际升级时验证','升级后使用9×9范围作业')
    text = text.replace('先验证','先检查').replace('验证真正运转，不能用拥有零件代替','观察机器真正运行并完成采掘').replace('别把法杖写成消耗品','法杖可以重复使用').replace('不能把两朵花都锁成必做','两种产能花任选一种').replace('库存六桶不代表设备自动连续运行','接通供料、供电与输出，持续处理原油').replace('不是材料箱交差','观察持续输入与输出').replace('filled_soul_vial','装满灵魂的瓶子')
    text = re.sub(r'#?[a-z0-9_.-]+:[a-z0-9_./-]+', lambda m:DISPLAY_NAMES.get(m[0].lstrip('#'),m[0]),text)
    text = text.replace('本次远征','远征').replace('本次配方图','配方图')
    text = text.replace('；', '。').replace(';', '。')
    kept = []
    for part in re.split(r'(?<=[。！？\n])', text):
        part = part.strip()
        if not part: continue
        if META_SENTENCE.search(part): continue
        part = re.sub(r'^(条件|行动|做法|所得|结果|下一步)[：:]\s*', '', part)
        part = re.sub(r'^(已证实的材料用途/加工去向（仅所选配方）|后续有证据的用途)[：:]\s*', '', part)
        part = part.replace('按本次配方图', '按配方图').replace('当前JEI', '配方查询').replace('JEI', '配方查询')
        part = part.replace('当前', '').replace('现行', '').replace('本包', '').replace('本版', '').replace('现版', '').replace('原生', '')
        part = part.replace('只作参考', '').replace('只作说明', '').replace('验收', '完成').replace('复用', '使用')
        part = part.replace('OR', '任选一种').replace('AND', '全部满足').replace('loops=1', '只循环一轮')
        part = re.sub(r'槽(\d+):', r'材料槽\1：', part)
        part = re.sub(r'\([^)]*(?:selected|scope|input|output|capability)[^)]*\)', '', part)
        part = part.replace('本组','').replace('本项','').replace('不是进入维度的强制门槛','进入维度不需要这件护具').replace('只在选择','仅在选择').replace('不强制同时','无需同时').replace('不能把两朵花都锁成必做','两种产能花任选一种').replace('不要求先完成铜浇铸节点','也可选择铜浇铸控制器的路线').replace('从节点取得粗赤钕','采掘赤钕晶簇').replace('验证','检查')
        part = part.replace('取得/操作 ', '取得').replace('验证','检查').replace('核实','检查')
        part = part.strip(' 。\n')
        if part: kept.append(part + ('。' if not part.endswith(('！', '？')) else ''))
    return player_replacements(''.join(kept))


def clean_title(title):
    title = {'纹章：视频三种不等于全部':'纹章与战斗技能','找矿层，不套旧视频高度':'在地下寻找矿石'}.get(title,title)
    title = title.replace('原生','').replace('OR来源','多种来源').replace('OR输入','任选材料')
    title = re.sub(r'^(复用[：:]\s*|引用现有\s*|参考[：:]\s*)', '', title)
    for a, b in [('原生进度', '成就'), ('原生路线', '浇铸路线'), ('当前', ''), ('本包', ''), ('本地', ''), ('真实', ''), ('确实', ''), ('验收', '完成'), ('核对', '查看'), ('分别验收', '分别完成'), ('版本边界', '后续探索')]: title = title.replace(a, b)
    title=player_replacements(title)
    return {'电子元件虽然ID叫blueprint却在组件装配':'装配电子元件','四激光二极管的组件配方':'装配4个激光二极管','到达终焉高原，保留未完工边界':'抵达终焉高原','纹章：视频三种不等于全部':'纹章与战斗技能','找矿层，不套旧视频高度':'在地下寻找矿石'}.get(title.strip(),title.strip())


def player_description(node, overrides=None):
    overrides = overrides or {}
    if 'description' in overrides: return list(overrides['description'])
    paragraphs = []
    for field in ('conditions', 'actions', 'outcomes', 'nextSteps'):
        values = node.get(field, [])
        if not isinstance(values, list): values = [values]
        for value in values:
            cleaned = clean_text(value)
            if cleaned and cleaned not in paragraphs: paragraphs.append(cleaned)
    if not paragraphs:
        target = node.get('target', {})
        paragraphs = [clean_title(node['title']) + '。']
    return paragraphs


def needs_operation(node, reused_item=False):
    if node.get('target', {}).get('kind') != 'item': return True
    title = node['title']
    return reused_item or bool(re.search(r'运行|运作|搭建|建造|验收|配置|供电|接通|接入|绑定|灌注|施法|吟唱|使用|转换|繁育|驯服|分流|维护|产线|测试|解锁|升级.*阶|三阶|二阶|研究|光明路径|黑暗路径|时运强化|太空强化|通道|自动合成|订单', title))


def task_for(node, key, catalog, advancements, reused_item=False):
    target = node.get('target', {}); kind, resource = target.get('kind'), target.get('id')
    result = []
    if kind == 'advancement':
        require(resource in advancements, f'Advancement not found in installed native resources: {key}/{resource}')
        result=[{'id': ident('task', key + '/advancement'), 'type': 'advancement', 'advancement': resource, 'criterion': ''}]
        if node.get('operationCheck'):result.append({'id':ident('task',key+'/operation'),'type':'checkmark','title':'完成操作'})
        return result
    if kind == 'item' and resource in catalog and not reused_item and not node.get('specificModelId'):
        amount = target.get('count', target.get('amount', 1))
        if type(amount) is not int or amount < 1: amount = 1
        result.append({'id': ident('task', key + '/item'), 'type': 'item', 'item': resource, 'count': amount,
                       'consume_items': False, 'only_from_crafting': False})
    if needs_operation(node, reused_item) or node.get('operationCheck') or node.get('specificModelId') or not result:
        result.append({'id': ident('task', key + '/operation'), 'type': 'checkmark', 'title': '完成操作'})
    return result


def native_resources(root, wanted):
    found = {}; unreadable = []
    for path in sorted((root / 'servers/cmi-expedition/instance/mods').glob('*.jar')):
        try:
            with zipfile.ZipFile(path) as archive:
                for resource in wanted - found.keys():
                    namespace, value = resource.split(':', 1)
                    entry = f'data/{namespace}/advancements/{value}.json'
                    try: blob = archive.read(entry)
                    except KeyError: continue
                    data = json.loads(blob)
                    require(isinstance(data.get('criteria'), dict) and data['criteria'], f'Native advancement has no criteria: {resource}')
                    found[resource] = {'jar': str(path.relative_to(root)), 'member': entry, 'sha256': sha(blob), 'criteria': list(data['criteria']), 'requirements': data.get('requirements')}
        except (zipfile.BadZipFile, OSError) as exc: unreadable.append({'path':str(path.relative_to(root)), 'reason':str(exc)})
    for base in [root / 'clients/cmi-expedition/instance/kubejs/data', root / 'servers/cmi-expedition/instance/kubejs/data']:
        for resource in wanted:
            ns, key = resource.split(':', 1); path = base / ns / 'advancements' / (key + '.json')
            if path.is_file():
                blob = path.read_bytes(); data = json.loads(blob)
                require(data.get('criteria'), f'Invalid data advancement: {path}')
                found[resource] = {'path': str(path.relative_to(root)), 'sha256':sha(blob), 'criteria':list(data['criteria']), 'requirements':data.get('requirements')}
    return found, unreadable


def asset_index(base, data):
    result = {}
    for row in data['assets']:
        path = Path(row['path'])
        if path.is_absolute(): actual = path
        elif data.get('pathBase'): actual = Path(data['pathBase']) / path
        else: actual = base / path
        require(actual.resolve().is_relative_to(ROOT), f'Asset escaped workspace: {actual}')
        result[row['id']] = (actual.resolve(), row)
    return result


class AssetPack:
    def __init__(self, payload): self.payload = payload; self.records = {}; self.resources = {}

    def add(self, key, path, expected=None, foreground=None):
        from PIL import Image
        blob = path.read_bytes()
        require(not expected or sha(blob) == expected, f'Asset hash changed: {path}')
        with Image.open(path) as im:
            im.load(); require(im.format == 'PNG', f'Not a true PNG: {path}'); img = im.convert('RGBA')
        sources = [{'path':str(path.relative_to(ROOT)), 'sha256':sha(blob)}]
        if foreground:
            fgpath, fgexpected = foreground; fgblob = fgpath.read_bytes()
            require(not fgexpected or sha(fgblob) == fgexpected, f'Foreground hash changed: {fgpath}')
            with Image.open(fgpath) as im:
                im.load(); require(im.format == 'PNG' and im.size == img.size, f'Recipe BG/FG dimensions differ: {fgpath}'); img.alpha_composite(im.convert('RGBA'))
            sources.append({'path':str(fgpath.relative_to(ROOT)), 'sha256':sha(fgblob)})
        require(img.width > 0 and img.height > 0, f'Empty image: {path}')
        import io
        memory=io.BytesIO(); img.save(memory, format='PNG'); output = memory.getvalue(); digest = sha(output)
        rel = f'kubejs/assets/{NAMESPACE}/textures/quests/{digest[:24]}.png'
        require(rel not in self.payload or self.payload[rel]==output, f'Image path collision: {rel}')
        self.payload[rel] = output
        self.records[digest] = {'relativePath':rel, 'sha256':digest, 'width':img.width, 'height':img.height, 'composited':bool(foreground), 'sources':sources}
        resource = f'{NAMESPACE}:textures/quests/{digest[:24]}.png'
        self.resources[resource] = rel
        width = min(img.width, 240); height = round(img.height * width / img.width)
        if img.width <= 64 and img.height <=64: width, height = img.width, img.height
        return f'{{image:{resource} width:{width} height:{height} align:center}}'

    def images(self, pipeline, node, assets):
        result = []; used=set()
        for figure in node.get('recipeFigures', []) + node.get('recipeImages', []):
            fg, bg = figure.get('foregroundAssetId'), figure.get('backgroundAssetId')
            if fg not in assets or bg not in assets: continue
            if (fg,bg) in used: continue
            used.add((fg,bg))
            fp, fr = assets[fg]; bp, br = assets[bg]
            result.append(self.add(pipeline+'/'+fg+'+'+bg, bp, br.get('sha256'), (fp,fr.get('sha256'))))
        recipe_parts = {value for pair in used for value in pair}
        for aid in node.get('assetIds', []):
            if aid in recipe_parts or aid not in assets: continue
            path,row = assets[aid]
            kind = str(row.get('kind','')) + ' ' + str(row.get('title',''))
            if re.search(r'recipe_(bg|img)|前景|背景|配方背景|配方前景', kind): continue
            result.insert(0, self.add(pipeline+'/'+aid, path, row.get('sha256')))
            break
        return list(dict.fromkeys(result))


def node_position(node, chapter):
    x, y = float(node.get('x', 0)), float(node.get('y', 0))
    if node.get('coordinateSpace', chapter.get('coordinateSpace')) in ('pixels','pixel'):
        scale=node.get('coordinateScale',chapter.get('coordinateScale')); require(scale, 'Pixel scale missing')
        sx,sy=(scale.get('x'),scale.get('y')) if isinstance(scale,dict) else (scale,scale)
        x/=sx;y/=sy
    require(math.isfinite(x) and math.isfinite(y), 'Nonfinite layout')
    return x, y


def validate_documents(documents, existing_ids, existing_quest_ids):
    ids=[]; quest_ids=set(existing_quest_ids); operations=items=advancements=lines=links=0
    for name, chapter in documents.items():
        for obj in walk(chapter):
            if 'id' in obj and HEX.fullmatch(str(obj['id'])):
                require(signed_id(obj['id']), f'Invalid signed 63 bit ID: {name}/{obj["id"]}'); ids.append(obj['id'])
        quest_ids.update(q['id'] for q in chapter['quests'])
    require(len(set(ids))==len(ids), 'New global ID collision')
    require(not (set(ids)&existing_ids), 'New ID collides with an existing quest object')
    for name, chapter in documents.items():
        local={f'q:{int(q["id"],16):x}' for q in chapter['quests']}
        local.update(key for image in chapter.get('images', []) if (key := anchor_key(image)))
        for q in chapter['quests']:
            require(not q.get('dependencies') and not q.get('rewards'), f'Unexpected new completion locks/rewards: {q["id"]}')
            require(q.get('description'), f'Missing player guide: {q["id"]}')
            require(all(not MODAL.search(t) for t in [q['title'],*q['description']] if not t.startswith('{image:')), f'Out-of-world player copy: {q["id"]}')
            for task in q['tasks']:
                if task['type']=='item':
                    items+=1; require(task.get('consume_items') is False, 'Item task consumes materials')
                elif task['type']=='advancement':
                    advancements+=1; require(task.get('criterion')=='', 'Partial advancement was substituted')
                else: operations+=1; require(task['type']=='checkmark' and task['title']=='完成操作', 'Unexpected operation detection')
        for link in chapter['quest_links']:
            links+=1; require(link['linked_quest'] in quest_ids, 'Linked quest target is missing')
            local.add(f'l:{int(link["id"],16):x}')
        for index,a in enumerate(chapter['quests']+chapter['quest_links']):
            for b in (chapter['quests']+chapter['quest_links'])[:index]:
                require(not (all(k in a and k in b for k in ('x','y')) and abs(a['x']-b['x'])<0.98 and abs(a['y']-b['y'])<1.0), f'Overlapping chapter objects: {name}/{a["id"]}/{b["id"]}')
        line_keys=[]
        for line in chapter['quest_enhance_decorative_lines']:
            lines+=1; require(len(line['nodes'])==2 and all(x in local for x in line['nodes']), f'Dangling local line endpoint: {name}/{line}')
            line_keys.append(tuple(line['nodes']))
        require(len(set(line_keys))==len(line_keys), f'Duplicate decorative lines: {name}')
    return {'newChapters':len(documents), 'newQuests':sum(len(c['quests']) for c in documents.values()),'itemTasks':items,'advancementTasks':advancements,'operationTasks':operations,'decorativeLines':lines,'nativeQuestLinks':links,'newObjectIds':len(ids),'hardFTBDependencies':0,'newRewards':0}


def build_stage(root=ROOT, output=OUT, overrides=None):
    require(output.resolve().is_relative_to(root / 'design/researched-quest-integration-20261018'), 'Staging output must stay in integration design folder')
    overrides=overrides or {}; node_overrides=overrides.get('nodes',{}); extra_exclusions=set(overrides.get('excludeNodeKeys',[])) | {'technology/C-space-integration-route','technology/B-compressed','technology/B-alloy-reference','technology/B-ii-reactor'}; edge_exclusions=set(overrides.get('excludeEdgeKeys',[])) | DEFAULT_EDGE_EXCLUSIONS
    catalog_path=root/'tools/quest-workbench/runs/20261018-022135/instance/jei-exports/items.json'
    catalog_data=json.loads(catalog_path.read_bytes());DISPLAY_NAMES.update({x['id']:x.get('n',x['id']) for x in catalog_data['items']});catalog={x['id']:x for x in catalog_data['items'] if x.get('k','').startswith('item|')}
    current=chapter_documents(root/INSTANCE_ROOTS[0]); existing_ids=set();existing_quests={};existing_adv={};existing_items=defaultdict(list);per_root_quests={}
    for relative in INSTANCE_ROOTS:
        docs=chapter_documents(root/relative);per_root_quests[relative]={q['id']:q for d in docs.values() for q in d.get('quests',[])}
        for path in sorted((root/relative/'config/ftbquests/quests').rglob('*.snbt')):
            for obj in walk(SNBT.loads(path.read_text())):
                if HEX.fullmatch(str(obj.get('id',''))):existing_ids.add(obj['id'].upper())
    for d in current.values():
        for obj in walk(d):
            if HEX.fullmatch(str(obj.get('id',''))):existing_ids.add(obj['id'].upper())
        for quest in d.get('quests',[]):
            existing_quests[quest['id']]=quest
            for task in quest.get('tasks',[]):
                if task.get('type')=='advancement' and task.get('criterion','')=='':existing_adv[task.get('advancement')]=quest['id']
                if task.get('type')=='item':
                    target=task.get('item');resource=target if isinstance(target,str) else target.get('id') if isinstance(target,dict) else None
                    if resource:existing_items[resource].append(quest['id'])
    sources=[]; all_nodes={}; all_edges=[]; all_chapters={}; catalogs={};provenance=[]
    for label, folder in PIPELINES:
        base=root/'design'/folder/'synthesis';tasks=json.loads((base/'task-structure.json').read_bytes());evidence=json.loads((base/'dependency-evidence.json').read_bytes());assets=json.loads((base/'asset-manifest.json').read_bytes())
        sources.append((label,base,tasks,evidence,assets));catalogs[label]=asset_index(base,assets)
        for filename in ['task-structure.json','dependency-evidence.json','asset-manifest.json']:
            path=base/filename;provenance.append({'path':str(path.relative_to(root)), 'sha256':sha(path.read_bytes())})
        for chapter in tasks['chapters']:all_chapters[label+'/'+chapter['id']]=chapter
        for node in tasks['nodes']:all_nodes[label+'/'+node['id']]=(label,node)
        all_edges += [(label,e) for e in tasks['edges']]
    wanted={n.get('target',{}).get('id') for _,n in all_nodes.values() if n.get('target',{}).get('kind')=='advancement'}
    advancements,unreadable=native_resources(root,wanted)
    excluded=[];reused=[];selected={};mapping={};payload={};pack=AssetPack(payload);enrichments=[]
    for key,(label,node) in all_nodes.items():
        override=node_overrides.get(key,{})
        node={**node,**DEFAULT_NODE_PATCHES.get(key,{}),**override.get('sourcePatch',{})}
        target=node.get('target',{});resource=target.get('id')
        if key in REUSE_OPERATIONS:
            existing_id=REUSE_OPERATIONS[key]
            require(existing_id in existing_quests, f'Reviewed existing operation is missing: {key}/{existing_id}')
            mapping[key]={'questId':existing_id,'reused':True,'chapterKey':None}
            reused.append({'nodeKey':key,'questId':existing_id,'method':'reviewed_equivalent_existing_operation'})
            enrichments.append({'nodeKey':key,'questId':existing_id,'title':clean_title(node['title']),'description':pack.images(label,node,catalogs[label])+player_description(node,override),'nonTextFieldsMustRemainUnchanged':True})
            continue
        if override.get('exclude') or key in extra_exclusions or node.get('currentPackStatus')!='present' or node.get('referenceOnly'):
            excluded.append({'nodeKey':key,'title':node['title'],'reason':override.get('reason','Uninstalled/unverified/reference-only branch')});continue
        if target.get('kind')=='advancement' and resource not in advancements:
            excluded.append({'nodeKey':key,'title':node['title'],'reason':'Native advancement not found in installed resources','resource':resource});continue
        if target.get('kind')=='advancement' and resource in existing_adv:
            mapping[key]={'questId':existing_adv[resource],'reused':True,'chapterKey':None};reused.append({'nodeKey':key,'questId':existing_adv[resource],'method':'exact_native_whole_advancement','resource':resource});continue
        if node['chapterId']=='A-bee':
            guide=next((q for q in existing_quests.values() if any('the_bumblezone_logo_large' in p for p in q.get('description',[]))),None)
            if guide:
                mapping[key]={'questId':guide['id'],'reused':True,'chapterKey':None};reused.append({'nodeKey':key,'questId':guide['id'],'method':'Bumblezone_existing_full_native_tree'});continue
        item_reused=target.get('kind')=='item' and bool(existing_items.get(resource))
        title=override.get('title',clean_title(node['title']));descriptions=player_description(node,override)
        descriptions=pack.images(label,node,catalogs[label])+descriptions
        task_rows=task_for(node,key,catalog,advancements,item_reused)
        chapter_key=label+'/'+node['chapterId'];chapter=all_chapters[chapter_key]
        x,y=node_position(node,chapter)
        icon=node.get('icon',{});icon=icon.get('item',resource) if isinstance(icon,dict) else icon
        if icon not in catalog:icon=resource if resource in catalog else 'minecraft:book'
        qid=ident('quest',key)
        quest={'id':qid,'title':title,'icon':icon,'x':x,'y':y,'optional':bool(node.get('optional',False)),'tasks':task_rows,'description':descriptions}
        if item_reused:
            reused.append({'nodeKey':key,'questId':qid,'method':'new_operation_reuses_existing_acquisition','existingQuestIds':existing_items[resource],'resource':resource})
        selected[key]={'quest':quest,'sourceNode':node,'label':label,'chapterKey':chapter_key};mapping[key]={'questId':qid,'reused':False,'chapterKey':chapter_key}
    documents={};by_chapter={}
    for chapter_key,chapter in all_chapters.items():
        members=[(key,value) for key,value in selected.items() if value['chapterKey']==chapter_key]
        if not members:continue
        label,cid=chapter_key.split('/',1);filename='research_'+('adventure_' if label=='adventure' else 'technology_')+re.sub(r'[^a-z0-9_]+','_',cid.lower())+'.snbt'
        quests=[value['quest'] for key,value in members]
        minx=min(q['x'] for q in quests);miny=min(q['y'] for q in quests)
        for q in quests:q['x']-=minx;q['y']-=miny
        for index,q in enumerate(quests):
            while any(abs(q['x']-other['x'])<0.98 and abs(q['y']-other['y'])<1.15 for other in quests[:index]):q['y']+=1.25
        doc={'id':ident('chapter',chapter_key),'filename':filename[:-5], 'title':clean_title(chapter['title']).replace('产线运行完成','产线运行'),'group':('54D4CAA40ADB5408' if label=='adventure' else '050255AE19A93344'),'order_index':200+len(documents),'icon':quests[0]['icon'],'consume_items':False,'default_quest_shape':'circle','default_hide_dependency_lines':False,'quests':quests,'quest_links':[],'quest_enhance_decorative_lines':[]}
        documents[filename]=doc;by_chapter[chapter_key]=doc
    edge_records=[];line_lookup=defaultdict(set);link_lookup={};filtered_edges=[]
    for label,edge in all_edges:
        source,target=label+'/'+edge['source'],label+'/'+edge['target'];edgekey=label+'/'+edge['id']
        if edgekey in edge_exclusions or source not in mapping or target not in mapping:
            filtered_edges.append({'edgeKey':edgekey,'source':source,'target':target,'reason':'Excluded endpoint or first-visit/return-visit ambiguity removed from display','originalEdge':edge});continue
        sm,tm=mapping[source],mapping[target]
        if sm['questId']==tm['questId']:continue
        destination=tm['chapterKey'] or sm['chapterKey']
        if destination is None:continue
        doc=by_chapter[destination]
        def endpoint(mapped, sourcekey):
            if mapped['chapterKey']==destination:return 'q:'+format(int(mapped['questId'],16),'x')
            lookup=(destination,mapped['questId'])
            if lookup not in link_lookup:
                index=len(doc['quest_links']);lid=ident('link',destination+'/'+mapped['questId'])
                link={'id':lid,'linked_quest':mapped['questId'],'x':-4.0-(index//24)*3.0,'y':float(index%24)*1.5,'size':0.75,'shape':'rsquare'}
                doc['quest_links'].append(link);link_lookup[lookup]=lid
            return 'l:'+format(int(link_lookup[lookup],16),'x')
        a,b=endpoint(sm,source),endpoint(tm,target)
        if (a,b) not in line_lookup[destination]:
            doc['quest_enhance_decorative_lines'].append({'nodes':[a,b]});line_lookup[destination].add((a,b))
        edge_records.append({'edgeKey':edgekey,'chapterKey':destination,'fromQuestId':sm['questId'],'toQuestId':tm['questId'],'nodes':[a,b],'relation':edge.get('relation'),'sourceHardMeaning':edge.get('hard',False),'ftbCompletionLock':False,'evidenceIds':edge.get('evidenceIds',[]),'originalEdge':edge})
    # Source synthesis coordinates are reference grids. Published chapters use
    # one horizontal row, including cross-chapter links, with no row wrapping.
    for doc in documents.values():
        horizontal_layout(doc)
    new_quest_ids={q['id'] for d in documents.values() for q in d['quests']}
    existing_link_targets={link['linked_quest'] for d in documents.values() for link in d['quest_links']} - new_quest_ids
    def signature(quest):
        rows=[]
        for task in quest.get('tasks',[]):
            item=task.get('item');item_id=item.get('id') if isinstance(item,dict) else item
            rows.append({'type':task.get('type'),'item':item_id,'count':task.get('count',1),'tag':item.get('tag') if isinstance(item,dict) else None,'advancement':task.get('advancement'),'criterion':task.get('criterion','')})
        return rows
    for relative,qmap in per_root_quests.items():
        require(existing_link_targets <= qmap.keys(),f'Reused link missing in {relative}: {sorted(existing_link_targets-qmap.keys())}')
        for row in enrichments:
            require(row['questId'] in qmap,f'Enrichment target missing in {relative}: {row["questId"]}')
            require(signature(qmap[row['questId']])==signature(existing_quests[row['questId']]),f'Enrichment target semantics differ in {relative}: {row["questId"]}')
    summary=validate_documents(documents,existing_ids,set(existing_quests))
    summary['existingLinkTargetsVerifiedInAllThreeRoots']=len(existing_link_targets)
    summary['enrichmentTargetsVerifiedInAllThreeRoots']=len(enrichments)
    for filename,doc in documents.items():
        blob=(snbt(doc)+'\n').encode();require(SNBT.loads(blob.decode())==doc,f'SNBT roundtrip failed: {filename}')
        payload['config/ftbquests/quests/chapters/'+filename]=blob
    # KubeJS' installed client resource provider loads assets automatically. A separate
    # ZIP copy would duplicate every texture and require resource-pack UI activation.
    assets_manifest={'namespace':NAMESPACE,'loader':'existing KubeJS assets resource provider','assets':list(pack.records.values()),'resourceMap':pack.resources}
    mapping_report={'sourceNodes':len(all_nodes),'selectedNodes':len(selected),'excludedNodes':excluded,'reuse':reused,'mapping':mapping,'relationships':edge_records,'excludedRelationships':filtered_edges,'reviewedNodePatches':DEFAULT_NODE_PATCHES,'nativeAdvancements':advancements,'unreadableArchives':unreadable}
    plan={'schemaVersion':1,'kind':'additive-researched-quest-install-v1','createdAt':datetime.now(timezone.utc).isoformat(),'stageRoot':str(output.relative_to(root)),'summary':summary,'inputProvenance':provenance,'guards':{},'chapterInventory':{},'writes':[],'excludedNodes':len(excluded),'reusedNativeQuests':sum(x['method']=='exact_native_whole_advancement' for x in reused),'referenceOnlyUnverifiedExcluded':True,'noExistingChapterOverwritten':True,'playerDataTouched':False}
    if REPLACEMENT_PATH.exists():plan['guards'][str(REPLACEMENT_PATH.relative_to(root))]=sha(REPLACEMENT_PATH.read_bytes())
    for record in provenance: plan['guards'][record['path']]=record['sha256']
    for label,base,tasks,evidence,assets in sources:
        for record in evidence['evidenceRecords']:
            p=record.get('path');digest=record.get('sha256')
            if p and digest:
                path=Path(p) if Path(p).is_absolute() else base/p
                require(path.resolve().is_relative_to(root),f'Evidence escaped workspace: {path}')
                actual=sha(read_safe(path));require(actual==digest,f'Review evidence changed: {record["id"]}/{path}')
                plan['guards'][str(path.relative_to(root))]=digest
    for record in pack.records.values():
        for source in record['sources']:plan['guards'][source['path']]=source['sha256']
    # Guard every existing chapter to catch game/editor saves after semantic matching.
    for relative in INSTANCE_ROOTS:
        base=root/relative
        plan['chapterInventory'][relative]=sorted(p.name for p in (base/'config/ftbquests/quests/chapters').glob('*.snbt'))
        for path in sorted((base/'config/ftbquests/quests').rglob('*.snbt')):plan['guards'][str(path.relative_to(root))]=sha(read_safe(path))
        for rel,blob in payload.items():
            path=base/rel;require(not path.exists(),f'Additive target already exists: {path}')
            plan['writes'].append({'path':str(path.relative_to(root)),'source':'payload/'+rel,'beforeSHA256':None,'afterSHA256':sha(blob),'bytes':len(blob)})
    manifest_path=root/'clients/cmi-expedition/evidence/overlay-files.json';manifest_blob=read_safe(manifest_path);manifest=json.loads(manifest_blob)
    plan['guards'][str(manifest_path.relative_to(root))]=sha(manifest_blob)
    for rel,blob in payload.items():require(rel not in manifest,f'Overlay manifest already owns new path: {rel}');manifest[rel]=sha(blob)
    after_manifest=json_bytes(manifest);payload_plan={'overlay-files.updated.json':after_manifest}
    plan['writes'].append({'path':str(manifest_path.relative_to(root)),'source':'overlay-files.updated.json','beforeSHA256':sha(manifest_blob),'afterSHA256':sha(after_manifest),'bytes':len(after_manifest)})
    output.mkdir(parents=True,exist_ok=True)
    for old in (output/'payload').rglob('*'):
        if old.is_file() and old.relative_to(output/'payload').as_posix() not in payload:old.unlink()
    for rel,blob in payload.items():atomic(output/'payload'/rel,blob)
    for rel,blob in payload_plan.items():atomic(output/rel,blob)
    atomic(output/'task-mapping.json',json_bytes(mapping_report));atomic(output/'asset-manifest.json',json_bytes(assets_manifest));atomic(output/'install-plan.json',json_bytes(plan))
    copy_rows=[{'nodeKey':key,'questId':value['quest']['id'],'title':value['quest']['title'],'description':[p for p in value['quest']['description'] if not p.startswith('{image:')],'tasks':value['quest']['tasks']} for key,value in selected.items()]
    atomic(output/'player-copy.json',json_bytes(copy_rows))
    atomic(output/'existing-copy-enrichments.json',json_bytes(enrichments))
    atomic(output/'README.md',('新增章节 '+str(summary['newChapters'])+'；新增任务 '+str(summary['newQuests'])+'。\n\n仅新增文件，现有任务语义复用与逐边关系见 task-mapping.json。所有配方边保留备选，不施加全局完成锁。\n\n默认生成草稿；通过内容审阅后使用 --apply-plan install-plan.json。安装会验证所有输入/目标哈希、备份 manifest 并原子回滚。\n').encode())
    return plan


def apply_plan(plan_path, root=ROOT, fail_after=None):
    plan_blob=read_safe(plan_path);plan=json.loads(plan_blob);require(plan.get('kind')=='additive-researched-quest-install-v1','Unexpected plan kind')
    stage=root/plan['stageRoot'];require(stage.resolve()==plan_path.parent.resolve(),'Plan does not bind its stage directory')
    guards=plan['guards'];writes=plan['writes'];require(writes,'Empty install plan')
    def safe(relative):
        path=root/relative;require(path.resolve().is_relative_to(root.resolve()) and not path.is_symlink(),f'Unsafe install path: {relative}');return path
    # New chapters/assets only, plus the explicitly scoped overlay file manifest.
    for row in writes:
        relative=row['path'];allowed=any(relative.startswith(prefix+'/config/ftbquests/quests/chapters/research_') and relative.endswith('.snbt') or relative.startswith(prefix+'/kubejs/assets/'+NAMESPACE+'/textures/quests/') and relative.endswith('.png') for prefix in INSTANCE_ROOTS)
        require(allowed or relative=='clients/cmi-expedition/evidence/overlay-files.json',f'Unapproved install target: {relative}')
        if allowed:require(row.get('beforeSHA256') is None,f'Additive plan cannot overwrite an existing chapter/asset: {relative}')
        source=stage/row['source'];require(source.resolve().is_relative_to(stage.resolve()),'Stage source escaped')
        require(sha(read_safe(source))==row['afterSHA256'],f'Staged file changed: {source}')
    for relative,names in plan.get('chapterInventory',{}).items():
        require(sorted(p.name for p in (root/relative/'config/ftbquests/quests/chapters').glob('*.snbt'))==names,f'Concurrent chapter addition/removal: {relative}')
    for relative,digest in guards.items():require(sha(read_safe(safe(relative)))==digest,f'Concurrent source edit: {relative}')
    for row in writes:require(sha(read_safe(safe(row['path'])))==row['beforeSHA256'],f'Concurrent target edit: {row["path"]}')
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-')+secrets.token_hex(3);backup=stage.parent/'backups'/stamp;backup.mkdir(parents=True)
    originals={row['path']:read_safe(safe(row['path'])) for row in writes};done=[]
    for relative,blob in originals.items():
        if blob is not None:atomic(backup/relative,blob)
    atomic(backup/'install-plan.json',plan_blob)
    try:
        for index,row in enumerate(writes):
            target=safe(row['path']);require(sha(read_safe(target))==row['beforeSHA256'],f'Concurrent target edit before write: {row["path"]}')
            atomic(target,read_safe(stage/row['source']));done.append(row['path'])
            require(sha(read_safe(target))==row['afterSHA256'],f'Post-write mismatch: {target}')
            if fail_after is not None and index+1>=fail_after:raise RuntimeError('Injected rollback test failure')
    except BaseException:
        for relative in reversed(done):
            target=safe(relative);current=read_safe(target);expected=next(x['afterSHA256'] for x in writes if x['path']==relative)
            require(sha(current)==expected,f'Rollback stopped to preserve concurrent edit: {relative}')
            if originals[relative] is None:target.unlink(missing_ok=True)
            else:atomic(target,originals[relative])
        atomic(backup/'rollback.json',json_bytes({'rolledBack':True,'writesUndone':len(done)}));raise
    receipt={'completedAt':datetime.now(timezone.utc).isoformat(),'planSHA256':sha(plan_blob),'backup':str(backup.relative_to(root)),'files':len(writes),'summary':plan['summary'],'installed':True,'existingChaptersChanged':False,'playerDataChanged':False}
    atomic(stage.parent/'install-result.json',json_bytes(receipt));return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=OUT);parser.add_argument('--overrides',type=Path);parser.add_argument('--apply-plan',type=Path);args=parser.parse_args()
    if args.apply_plan:result=apply_plan(args.apply_plan)
    else:result=build_stage(output=args.output,overrides=json.loads(args.overrides.read_text()) if args.overrides else None)
    print(json.dumps(result.get('summary',result),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
