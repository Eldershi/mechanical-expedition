#!/usr/bin/env python3
"""Merge the authorized equipment and flower branch without rewriting other quests."""
from pathlib import Path
from datetime import datetime
from copy import deepcopy
import fcntl
import hashlib
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('quest_surgery', ROOT / 'design/researched-quest-integration-20261018/finish_existing_copy.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
WARRIOR = '74B9E37643840B33'
FLOWER = '70AB9E00ED2D0BEB'
GUARDIAN = '54BBD39DA4808D33'
NAME = 'bumblezone_01_exploration.snbt'


def task_id(key):
    return hashlib.sha256(('bumblezone-equipment-merge:' + key).encode()).hexdigest()[:16].upper()


def item_task(key, title, choices, old_id=None):
    item = choices[0] if len(choices) == 1 else {
        'id': 'itemfilters:or', 'Count': 1,
        'tag': {'items': [{'id': value, 'Count': 1} for value in choices]},
    }
    return {'id': old_id or task_id(key), 'type': 'item', 'title': title,
            'item': item, 'count': 1, 'consume_items': False, 'only_from_crafting': False}


def replace_list(text, key, rows):
    match = re.search(r'(?m)^\t' + re.escape(key) + r':\s*\[', text)
    assert match
    start = match.end() - 1
    depth = 0
    for token in s.TOKEN.finditer(text, start):
        if token.group() == '[':
            depth += 1
        elif token.group() == ']':
            depth -= 1
            if depth == 0:
                return text[:start] + s.g.snbt(rows, 1) + text[token.end():]
    raise AssertionError('unclosed list')


def make_candidate(blob):
    old = s.loads(blob.decode())
    assert len(old['quests']) == 133
    selected = {q['id'] for q in old['quests'] if any(
        task.get('advancement', '').split(':')[-1].split('/')[0]
        in {'armor', 'stinger_spear', 'honey_crystal_shield'} for task in q.get('tasks', []))}
    assert len(selected) == 18
    keep = {WARRIOR, FLOWER, GUARDIAN}
    removed = selected - keep
    original = {q['id']: q for q in old['quests']}
    assert all(not original[q].get('rewards') for q in selected)
    updated = {qid: deepcopy(original[qid]) for qid in keep}
    prefix = 'the_bumblezone:'
    warrior = updated[WARRIOR]
    warrior['tasks'] = [
        item_task('helmet', '无刺蜜蜂头盔', [prefix + 'stingless_bee_helmet_' + i for i in ['1', '2']], warrior['tasks'][0]['id']),
        item_task('chestplate', '大黄蜂胸甲', [prefix + v for v in ['bumble_bee_chestplate_1', 'bumble_bee_chestplate_2', 'bumble_bee_chestplate_trans_1', 'bumble_bee_chestplate_trans_2']]),
        item_task('leggings', '蜜蜂护腿', [prefix + 'honey_bee_leggings_' + i for i in ['1', '2']]),
        item_task('boots', '木匠蜂靴子', [prefix + 'carpenter_bee_boots_' + i for i in ['1', '2']]),
        item_task('spear', '螫针矛', [prefix + 'stinger_spear']),
        item_task('shield', '蜂蜜结晶盾牌', [prefix + 'honey_crystal_shield']),
    ]
    warrior['description'] = [
        '装备蜜蜂所能提供的武器和盔甲！收集无刺蜜蜂头盔、大黄蜂胸甲、蜜蜂护腿、木匠蜂靴子、螫针矛和蜂蜜结晶盾牌各一件。每类护甲选择喜欢的款式即可。',
        '复眼：戴上无刺蜜蜂头盔后潜行，周围的蜜蜂和巨蜂会显出轮廓，找蜂不必再靠听声辨位。',
        '那是一只鸟！那是一架飞机！不，那是……穿着大黄蜂胸甲的你！跳起后按住跳跃键，可以短暂飞行。搭配更多蜜蜂装备或饰品，飞行时间也会延长。',
        '这是蜜蜂的膝盖！穿着蜜蜂护腿走过花朵或花粉堆，可以收集花粉；积满后潜行会释放花粉球。洗澡时间！进入水中或走过湿海绵可以洗去花粉。',
        '地板烫脚！木匠蜂靴子能让你在原木、木板、树叶和蜜脾墙面上攀附、蹬跳。强大的大腿！站在这些方块中央，向下看并潜行，还能自动挖掘脚下的方块。',
        '超越武器……螫针矛可以近战，也能投掷：成为蜜蜂！用它让敌人中毒；停滞不前！继续尝试麻痹敌人。面对高血量目标时，麻痹能帮你赢得有利的胜算；一次漂亮的远投，就是值得称赞的标枪投掷。',
        '无敌的防御！蜂蜜结晶盾牌能短暂减缓近身攻击者，但新盾还很脆弱。无法阻挡的攻击获胜！爆炸和火焰会对盾牌造成大量损耗，别把每一种攻击都交给它硬接。想成为大蜂巢的守护者，就继续在铁砧上强化它。',
    ]
    flower = updated[FLOWER]
    flower['tasks'] = [item_task('flower', '花朵头饰', [prefix + 'flower_headwear'], flower['tasks'][0]['id'])]
    flower['description'] = [
        '制作或获得一顶花朵头饰，戴上它，把自己装扮成一朵会走路的大花，吸引蜜蜂靠近！',
        '这是一种声明！像皮革护甲一样，花朵头饰也能用染料染色；挑一种喜欢的颜色，不必把所有颜色都收集一遍。',
        '好奇的蜜蜂：戴着花朵头饰进入巢室迷宫，可以避免因进入这座结构而招来蜂巢之怒。它也能帮助已有的蜂巢之怒更快消退。',
    ]
    guardian = updated[GUARDIAN]
    guardian['x'], guardian['y'] = 6.475, warrior['y']
    guardian['description'] = [
        '新做的蜂蜜结晶盾牌只是起点。带上蜂蜜结晶碎片，在铁砧上反复修复盾牌，逐步提升盾牌等级，直到九级，成为大蜂巢的守护者！',
        '最高等级的盾牌拥有约为原版盾牌两倍的耐久，但依然惧怕火焰与爆炸。升级提高的是盾牌的底子，并不会抹去这些弱点。',
    ]
    # Preserve the existing native level-nine check; it accepts any damage/enchantments.
    assert guardian['tasks'] == original[GUARDIAN]['tasks']
    remap = {}
    for qid in selected:
        task = original[qid]['tasks'][0]['advancement']
        target = FLOWER if any(k in task for k in ['craft_flower_headwear', 'dye_flower_headwear', 'flower_headwear_wrath_structure']) else GUARDIAN if qid == GUARDIAN else WARRIOR
        remap['q:' + format(int(qid, 16), 'x')] = 'q:' + format(int(target, 16), 'x')
    lines = []
    seen = set()
    for line in old['quest_enhance_decorative_lines']:
        nodes = [remap.get(node, node) for node in line['nodes']]
        nodes = [node for index, node in enumerate(nodes) if index == 0 or node != nodes[index - 1]]
        if len(nodes) < 2 or tuple(nodes) in seen:
            continue
        seen.add(tuple(nodes))
        lines.append(dict(line, nodes=nodes))
    text = blob.decode()
    for qid in selected:
        start, end = s.quest_span(text, qid)
        text = text[:start] + (s.g.snbt(updated[qid], 2) if qid in keep else '') + text[end:]
    text = replace_list(text, 'quest_enhance_decorative_lines', lines)
    candidate = s.loads(text)
    assert len(candidate['quests']) == 118
    new_by_id = {q['id']: q for q in candidate['quests']}
    assert all(new_by_id[qid] == q for qid, q in original.items() if qid not in selected)
    unchanged = {k: v for k, v in old.items() if k not in ['quests', 'quest_enhance_decorative_lines']}
    assert all(candidate[k] == v for k, v in unchanged.items())
    ids = re.findall(r'\bid: "([0-9A-Fa-f]{16})"', text)
    assert len(ids) == len(set(ids))
    assert all(qid not in text for qid in removed)
    return text.encode(), removed, updated


def main():
    manifest = ROOT / 'clients/cmi-expedition/evidence/overlay-files.json'
    roots = [ROOT / p / 'config/ftbquests/quests' for p in ['clients/cmi-expedition/instance', 'clients/cmi-expedition/overlay', 'servers/cmi-expedition/instance']]
    with (manifest.parent / '.overlay-files.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before, writes = {}, {}
        for root in roots:
            path = root / 'chapters' / NAME
            before[path] = path.read_bytes()
            writes[path], removed, updated = make_candidate(before[path])
            for other in root.rglob('*.snbt'):
                if other == path:
                    continue
                contents = other.read_text()
                assert all(qid not in contents for qid in removed), ('external reference', other)
        assert len(set(writes.values())) == 1
        before[manifest] = manifest.read_bytes()
        merged = json.loads(before[manifest])
        merged['config/ftbquests/quests/chapters/' + NAME] = s.sha(next(iter(writes.values())))
        writes[manifest] = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode()
        backup = OUT / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
        for path, blob in before.items():
            assert path.read_bytes() == blob, ('concurrent edit', path)
            s.atomic(backup / path.relative_to(ROOT), blob)
        done = []
        try:
            for path, blob in writes.items():
                assert path.read_bytes() == before[path], ('concurrent edit', path)
                s.atomic(path, blob)
                done.append(path)
                assert path.read_bytes() == blob
        except BaseException:
            for path in reversed(done):
                assert path.read_bytes() == writes[path]
                s.atomic(path, before[path])
            raise
        report = {'applied': True, 'beforeQuests': 133, 'afterQuests': 118, 'mergedBranchBefore': 18, 'mergedBranchAfter': 3,
                  'untouchedQuestObjects': 115, 'threeRootsIdentical': True, 'backupRoot': str(backup),
                  'nodes': updated, 'removedQuestIds': sorted(removed),
                  'files': [{'path': str(p.relative_to(ROOT)), 'beforeSha256': s.sha(before[p]), 'afterSha256': s.sha(b)} for p, b in writes.items()]}
        s.atomic(OUT / 'install-result.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode())
        print(json.dumps({k: v for k, v in report.items() if k not in ['nodes', 'removedQuestIds', 'files']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
