#!/usr/bin/env python3
"""Consolidate the whole Bumblezone chapter and draw direct parallel matrices."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime
import fcntl
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('equipment_helpers', ROOT / 'design/bumblezone-equipment-merge-20261018/merge_equipment.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
s = m.s
P = 'the_bumblezone:'


def ref(qid):
    return 'q:' + format(int(qid, 16), 'x')


def candidate(blob):
    old = s.loads(blob.decode())
    assert len(old['quests']) == 117
    original = {q['id']: q for q in old['quests']}
    title = {q['title']: q['id'] for q in old['quests']}
    quests = deepcopy(original)
    remap = {ref(qid): ref(qid) for qid in quests}
    merged = []
    used = set()

    def group(keep, members, items=None, intro=None, source=None, descriptions=None):
        qid = title[keep]
        member_ids = [title[name] for name in members]
        assert qid in member_ids and not set(member_ids) & used
        used.update(member_ids)
        node = quests[qid]
        assert all(not original[i].get('rewards') for i in member_ids)
        if items:
            node['tasks'] = [m.item_task('consolidated:' + keep + ':' + str(i), label, [P + v if ':' not in v else v for v in choices], original[qid]['tasks'][0]['id'] if i == 0 else None)
                             for i, (label, choices) in enumerate(items)]
        elif source:
            node['tasks'] = deepcopy(original[title[source]]['tasks'])
        if descriptions is not None:
            node['description'] = descriptions
        else:
            notes = [intro] if intro else []
            seen = set(notes)
            for mid in member_ids:
                paragraphs = [p for p in original[mid].get('description', []) if p and not p.startswith('{image:')]
                for index, text in enumerate(paragraphs):
                    if text not in seen:
                        seen.add(text)
                        notes.append((original[mid]['title'] + '：' if len(member_ids) > 1 and index == 0 else '') + text)
            node['description'] = notes
        for mid in member_ids:
            remap[ref(mid)] = ref(qid)
            if mid != qid:
                quests.pop(mid)
        merged.append({'title': keep, 'before': len(member_ids), 'after': 1})

    group('蜜蜂领域', ['蜜蜂领域', '蜜蜂领域手册'])
    group('蜜蜂的维度等待着你！', ['蜜蜂的维度等待着你！', '蜜蜂传送门入侵！', '蜜汁液压机'], descriptions=[
        '蜜蜂的维度等待着你！用末影珍珠击中蜂巢或蜂箱，或尝试用活塞把自己推入蜂巢，从熟悉的方块里打开一场不熟悉的远征。',
        '蜜蜂传送门入侵！与蜜汁液压机是两种进入方法，选择一种即可。出发前带好食物、照明和返程装备。'])
    entry = quests[title['蜜蜂的维度等待着你！']]
    entry['tasks'] = [{'id': original[entry['id']]['tasks'][0]['id'], 'type': 'dimension', 'dimension': P + 'the_bumblezone'}]
    group('这是什么？...', ['这是什么？...', '医生在此！', '蜂巢大英雄！', '蜜蜂收藏家', '发现闪亮的！'],
          [('嗡嗡公文包', ['buzzing_briefcase'])], '一只公文包，装下一支蜂群。收集一只嗡嗡公文包，捕捉、照料和释放蜜蜂的诀窍都记在这里。')
    group('蜜蜂探险家', ['蜜蜂探险家', '这还算指南针吗..?', '蜜蜂地理', '观察蜜蜂', '迷失在巢室中', '园丁和蜜蜂'],
          [('蜂蜜指南针', ['honey_compass'])], '带上一只蜂蜜指南针，探索不同生物群系、巢室迷宫和花园。遇见新结构时，记下位置，再决定下一处目的地。')
    group('魔法烛光', ['魔法烛光', '设置氛围', '彩虹之上！', '启动我的陷阱蜡烛！'],
          [('大蜡烛', ['super_candle']), ('药水蜡烛', ['potion_candle'])], '准备大蜡烛和药水蜡烛各一份。染色、灵魂火焰和药水效果是同一套蜡烛玩法的不同用法。')
    group('大胆而鲁莽！', ['大胆而鲁莽！', '完美的设计', '正确的方向'],
          [('可雕刻蜡', ['carvable_wax']), ('古蜡砖', ['ancient_wax_bricks']), ('发光蜡通道', ['luminescent_wax_channel_red'])])
    group('免费的房产！（给蜜蜂）', ['免费的房产！（给蜜蜂）', '蜂蜡忍者', '从蜜蜂那里收集更多租金'],
          [('蜂巢蜜蜡', ['beehive_beeswax'])])
    group('明智的选择', ['明智的选择', '吃、吃、吃！'], source='明智的选择')
    colors = ['white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime', 'pink', 'gray', 'light_gray', 'cyan', 'purple', 'blue', 'brown', 'green', 'red', 'black']
    group('60年代的回归！', ['60年代的回归！', '蜜蜂阻挡墙', '彩虹绳帘！！！'],
          [('任意颜色的绳帘', ['string_curtain_' + c for c in colors])], '选择任意一种颜色的绳帘即可。布置、延长与阻挡蜜蜂的用法放在一起，不必为了换色重复完成任务。')
    group('肮脏的回报', ['肮脏的回报', '天空决斗'], [('泥球', ['dirt_pellet'])])
    group('不再愤怒！只有友谊！', ['不再愤怒！只有友谊！', '不要蜜蜂！！！', '和平的蜜糖祭品'], source='不再愤怒！只有友谊！')
    group('赢得青睐', ['赢得青睐', '看哪！我的蜜蜂！'], source='赢得青睐')
    group('危险的酿造', ['危险的酿造', '浓缩毒素', '欺骗机会！'])
    # Three distinct potion results remain three subtasks in one brewing quest.
    quests[title['危险的酿造']]['tasks'] = [deepcopy(original[title[name]]['tasks'][0]) for name in ['危险的酿造', '浓缩毒素', '欺骗机会！']]
    group('更多蜜蜜！！！', ['更多蜜蜜！！！', '快速成长！', '爱正在蔓延！', '蜜蜂农夫'], [('蜂蜜桶', ['honey_bucket'])])
    group('获得皇家力量', ['获得皇家力量', '高超的收集者', '拉！不要推！'],
          [('蜂王浆瓶', ['royal_jelly_bottle']), ('蜂王浆桶', ['royal_jelly_bucket']), ('蜂王浆块', ['royal_jelly_block'])])
    group('美丽的晶体！', ['美丽的晶体！', '咬碎牙齿的零食', '让光芒闪耀！'],
          [('蜂蜜结晶碎片', ['honey_crystal_shards']), ('蜂蜜结晶', ['honey_crystal']), ('闪耀蜂蜜结晶', ['glistering_honey_crystal'])])
    group('蜜糖回收者', ['蜜糖回收者', '更加黏稠的局面！', '清洁狂人！', '用蜜思考！', '粘性的力量！'],
          [('粘性蜂蜜残留物', ['sticky_honey_residue']), ('红石粘性蜂蜜残留物', ['sticky_honey_redstone']), ('蜂蜜蜘蛛网', ['honey_web']), ('红石蜂蜜蜘蛛网', ['redstone_honey_web'])],
          '把黏糊糊的东西收进一套工具箱：残留物、红石残留物和两种蜂蜜蜘蛛网各准备一份，清理、回收和机关用途一起掌握。')
    group('蜜蜂之力！', ['蜜蜂之力！', '谁需要蜜蜂？？？'], source='谁需要蜜蜂？？？')
    group('战术花粉', ['战术花粉', '没有鼻塞也没有摔断膝盖！', '奇怪的文物...'], [('花粉堆', ['pile_of_pollen']), ('可疑的花粉堆', ['pile_of_pollen_suspicious'])])
    group('蜜蜂授粉专家', ['蜜蜂授粉专家', '蜜蜂清洁！', '无效的攻击！', '蘑菇、花朵，同样的事情', '祝福你，熊猫！', '蜜蜂全垒打！'], [('花粉球', ['pollen_puff'])])
    group('花卉分享', ['花卉分享', '这是什么意思？！'], source='花卉分享')
    group('糖分学', ['糖分学', '糖分爆棚！！！', '很快...所有的都将是甘蔗！'],
          [('糖水桶', ['sugar_water_bucket']), ('糖水瓶', ['sugar_water_bottle']), ('糖渍圆石', ['sugar_infused_cobblestone'])])
    group('极限人群控制', ['极限人群控制', '你最好表现好！'], [('结晶炮', ['crystal_cannon']), ('蜜蜂炮', ['bee_cannon'])])
    group('蜜蜂战士崛起！', ['蜜蜂战士崛起！', '无尽的刺痛'])
    # Keep the six-equipment checklist already accepted in the previous edit.
    quests[title['蜜蜂战士崛起！']]['tasks'] = deepcopy(original[title['蜜蜂战士崛起！']]['tasks'])

    # Place each small thematic branch on one horizontal lane: no alternating y offsets.
    lanes = [
        ['更甜蜜的梦！', '这是什么？...', '蜜蜂电影但是它变大了300%！', '皇家朋友直到最后！', '花卉分享', '个人守卫'],
        ['不再愤怒！只有友谊！', '赢得青睐', '快速的嗡嗡蜜蜂！', '成为一朵花！', '蜜蜂战士崛起！', '大蜂巢的守护者'],
        ['更多蜜蜜！！！', '美丽的晶体！', '蜜糖回收者', '糖分学', '获得皇家力量', '蜜蜂之力！'],
        ['免费的房产！（给蜜蜂）', '轻柔的触摸', '大胆而鲁莽！', '魔法烛光', '60年代的回归！', '时尚潮流！', '蜜蜂之舞！'],
        ['战术花粉', '蜜蜂授粉专家', '明智的选择', '刺激的美食', '危险的酿造'],
        ['俯冲出口', '蜜蜂钓鱼', '肮脏的回报', '极限人群控制', '可放置的气流！'],
    ]
    for row, names in enumerate(lanes):
        for col, name in enumerate(names):
            quests[title[name]]['x'] = round(-10.9 + col * 1.65, 3)
            quests[title[name]]['y'] = round(-7.0 + row * 1.6, 3)
    main = ['蜜蜂领域', '蜜蜂的维度等待着你！', '蜜蜂探险家', '去见女王！', '皇家存在', '女王的愿望']
    for col, name in enumerate(main):
        quests[title[name]]['x'], quests[title[name]]['y'] = round(-12.55 + col * 1.65, 3), 6.0
    wish_names = ['淹没住房市场', '蜘蛛太多', '醉蜜', '花粉战斗', '与虫群作战', '毒液战争', '黏液有丝分裂', '恐怖之牙', '重返战斗', '疯狂的花商', '极限低效', '饥饿的蜜蜂', '爱蜜蜂', '异界螨虫', '伟大的屠龙勇士', '疯狂的交易商']
    challenge_names = ['无尽的愤怒', '全知者', '和平与爱', '生命的祝福', '太阳能驱动', '现实故障']
    for index, name in enumerate(wish_names):
        row, col = divmod(index, 4)
        quests[title[name]]['x'], quests[title[name]]['y'] = round(-2.65 + col * 1.55, 3), round(3.675 + row * 1.55, 3)
    quests[title['希望、爱、梦想和蜜蜂！！！']]['x'], quests[title['希望、爱、梦想和蜜蜂！！！']]['y'] = 4.2, 6.0
    quests[title['古老的起源']]['x'], quests[title['古老的起源']]['y'] = 5.85, 6.0
    for index, name in enumerate(challenge_names):
        row, col = divmod(index, 2)
        quests[title[name]]['x'], quests[title[name]]['y'] = round(7.5 + col * 1.55, 3), round(4.45 + row * 1.55, 3)
    placed = {title[n] for lane in lanes for n in lane} | {title[n] for n in main + wish_names + challenge_names + ['希望、爱、梦想和蜜蜂！！！', '古老的起源']}
    assert placed == set(quests), ('unplaced', [q['title'] for qid, q in quests.items() if qid not in placed])
    queen_ids = {title[n] for n in wish_names + challenge_names + ['女王的愿望', '希望、爱、梦想和蜜蜂！！！', '古老的起源']}
    lines, seen = [], set()

    def line(a, b):
        if a != b and (a, b) not in seen:
            seen.add((a, b))
            lines.append({'nodes': [a, b]})

    # Collapse old category connections, dropping all intermediate queen routing anchors.
    for edge in old['quest_enhance_decorative_lines']:
        nodes = edge['nodes']
        if len(nodes) != 2 or any(not n.startswith('q:') for n in nodes):
            continue
        a, b = [remap.get(n, n) for n in nodes]
        if a in {ref(i) for i in queen_ids} or b in {ref(i) for i in queen_ids}:
            continue
        line(a, b)
    for a, b in zip(main, main[1:]):
        line(ref(title[a]), ref(title[b]))
    for name in wish_names:
        line(ref(title['女王的愿望']), ref(title[name]))
        line(ref(title[name]), ref(title['希望、爱、梦想和蜜蜂！！！']))
    line(ref(title['希望、爱、梦想和蜜蜂！！！']), ref(title['古老的起源']))
    for name in challenge_names:
        line(ref(title['古老的起源']), ref(title[name]))
    doc = deepcopy(old)
    doc['quests'] = [quests[q['id']] for q in old['quests'] if q['id'] in quests]
    doc['quest_enhance_decorative_lines'] = lines
    doc['images'] = [im for im in doc['images'] if not str(im.get('click', '')).startswith('quest_enhance:decorative_anchor:')]
    for im in doc['images']:
        if im['image'].endswith('the_bumblezone_logo_large.png'):
            im.update(x=-9.0, y=8.9, width=4.0, height=1.48)
        elif im['image'].endswith('bee_queen.png'):
            im.update(x=-4.3, y=8.9, width=1.2, height=1.2)
        else:
            im.update(x=4.2, y=8.6, width=0.9, height=0.9)
    # Preserve readable joke titles in the merged prose, and validate every reference.
    valid_refs = {ref(qid) for qid in quests}
    assert all(set(edge['nodes']) <= valid_refs for edge in lines)
    overlaps = []
    for index, a in enumerate(doc['quests']):
        for b in doc['quests'][index + 1:]:
            if abs(a['x'] - b['x']) < 1.08 and abs(a['y'] - b['y']) < 1.08:
                overlaps.append([a['title'], b['title']])
    assert not overlaps, overlaps
    ids = [t['id'] for q in doc['quests'] for t in q.get('tasks', [])] + list(quests)
    assert len(ids) == len(set(ids))
    assert sum(edge['nodes'][0] == ref(title['女王的愿望']) for edge in lines) == 16
    assert sum(edge['nodes'][1] == ref(title['希望、爱、梦想和蜜蜂！！！']) for edge in lines) == 16
    assert sum(edge['nodes'][0] == ref(title['古老的起源']) for edge in lines) == 6
    for qid, q in quests.items():
        assert q.get('dependencies', []) == original[qid].get('dependencies', [])
    result = (s.g.snbt(doc) + '\n').encode()
    assert s.loads(result.decode()) == doc
    removed = set(original) - set(quests)
    return result, {'beforeQuests': 117, 'afterQuests': len(quests), 'mergedCategories': merged,
                    'wishConnectionsOut': 16, 'wishConnectionsIn': 16, 'sanctumConnectionsOut': 6,
                    'wishMatrix': '4 rows x 4 columns', 'challengeMatrix': '3 rows x 2 columns',
                    'topLanesHaveConstantY': True, 'routingAnchors': 0, 'cardOverlaps': overlaps,
                    'dependenciesPreserved': True, 'removedQuestIds': sorted(removed)}


def main():
    manifest = ROOT / 'clients/cmi-expedition/evidence/overlay-files.json'
    roots = [ROOT / p / 'config/ftbquests/quests' for p in ['clients/cmi-expedition/instance', 'clients/cmi-expedition/overlay', 'servers/cmi-expedition/instance']]
    with (manifest.parent / '.overlay-files.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before, writes = {}, {}
        for root in roots:
            path = root / 'chapters' / m.NAME
            before[path] = path.read_bytes()
            writes[path], report = candidate(before[path])
            for other in root.rglob('*.snbt'):
                if other == path:
                    continue
                text = other.read_text()
                assert all(qid not in text for qid in report['removedQuestIds']), ('external reference', other)
        assert len(set(writes.values())) == 1
        before[manifest] = manifest.read_bytes()
        merged = json.loads(before[manifest])
        merged['config/ftbquests/quests/chapters/' + m.NAME] = s.sha(next(iter(writes.values())))
        writes[manifest] = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode()
        backup = OUT / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
        for path, blob in before.items():
            assert path.read_bytes() == blob
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
        report.update(applied=True, threeRootsIdentical=True, backupRoot=str(backup))
        s.atomic(OUT / 'install-result.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode())
        print(json.dumps({k: v for k, v in report.items() if k not in ['mergedCategories', 'removedQuestIds']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
