#!/usr/bin/env python3
"""Position the retained graph by its actual layers instead of thematic rows."""
from pathlib import Path
from datetime import datetime
from copy import deepcopy
import collections
import fcntl
import graphlib
import importlib.util
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('consolidation', OUT / 'consolidate.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
s = c.s


def project(values, gap=1.4):
    blocks = []
    for index, value in enumerate(values):
        blocks.append([value - index * gap, 1, [index]])
        while len(blocks) > 1 and blocks[-2][0] > blocks[-1][0]:
            b = blocks.pop()
            a = blocks.pop()
            n = a[1] + b[1]
            blocks.append([(a[0] * a[1] + b[0] * b[1]) / n, n, a[2] + b[2]])
    result = [0.0] * len(values)
    for value, _, indices in blocks:
        for index in indices:
            result[index] = value + index * gap
    return result


def build(blob):
    old = s.loads(blob.decode())
    assert len(old['quests']) == 65
    doc = deepcopy(old)
    q = {c.ref(n['id']): n for n in doc['quests']}
    names = {n['title']: r for r, n in q.items()}
    queen = {r for r, n in q.items() if any(':the_queens_desire/' in t.get('advancement', '') or ':essence/' in t.get('advancement', '') or 'enter_sempiternal_sanctum' in t.get('advancement', '') for t in n.get('tasks', []))}
    pred = {r: set() for r in q if r not in queen}
    for edge in doc['quest_enhance_decorative_lines']:
        a, b = edge['nodes']
        if a in pred and b in pred:
            # A reciprocal decorative edge arose when the protection tips were
            # merged. Ignore its feedback direction only for assigning ranks;
            # preserve both actual relation objects byte-for-byte in the file.
            if q[a]['title'] == '不再愤怒！只有友谊！' and q[b]['title'] == '赢得青睐':
                continue
            pred[b].add(a)
    order = list(graphlib.TopologicalSorter(pred).static_order())
    depth = {}
    for node in order:
        depth[node] = max((depth[p] + 1 for p in pred[node]), default=0)
    layers = collections.defaultdict(list)
    for node in order:
        layers[depth[node]].append(node)
    succ = collections.defaultdict(set)
    for node, parents in pred.items():
        for parent in parents:
            succ[parent].add(node)
    ys = {node: q[node]['y'] for node in order}
    for sweep in range(24):
        forward = sweep % 2 == 0
        for rank in sorted(layers, reverse=not forward):
            nodes = layers[rank]
            neighbours = pred if forward else succ
            desired = {node: sum(ys[n] for n in neighbours[node]) / len(neighbours[node]) if neighbours[node] else ys[node] for node in nodes}
            nodes.sort(key=lambda node: (desired[node], ys[node]))
            values = project([desired[node] for node in nodes])
            for node, value in zip(nodes, values):
                ys[node] = value
    centre = (min(ys.values()) + max(ys.values())) / 2
    for node in order:
        q[node]['x'] = round(-12.0 + depth[node] * 1.75, 3)
        q[node]['y'] = round(ys[node] - centre, 3)
    # Keep the requested matrices together, below the final exploration branch.
    royal = q[names['皇家存在']]
    centre_y = max(n['y'] for r, n in q.items() if r not in queen) + 3.0
    start_x = royal['x'] + 1.75
    q[names['女王的愿望']].update(x=round(start_x, 3), y=round(centre_y, 3))
    wish_names = ['淹没住房市场', '蜘蛛太多', '醉蜜', '花粉战斗', '与虫群作战', '毒液战争', '黏液有丝分裂', '恐怖之牙', '重返战斗', '疯狂的花商', '极限低效', '饥饿的蜜蜂', '爱蜜蜂', '异界螨虫', '伟大的屠龙勇士', '疯狂的交易商']
    for index, name in enumerate(wish_names):
        row, col = divmod(index, 4)
        q[names[name]].update(x=round(start_x + 1.75 + col * 1.45, 3), y=round(centre_y - 2.175 + row * 1.45, 3))
    ex = start_x + 7.85
    q[names['希望、爱、梦想和蜜蜂！！！']].update(x=round(ex, 3), y=round(centre_y, 3))
    q[names['古老的起源']].update(x=round(ex + 1.75, 3), y=round(centre_y, 3))
    for index, name in enumerate(['无尽的愤怒', '全知者', '和平与爱', '生命的祝福', '太阳能驱动', '现实故障']):
        row, col = divmod(index, 2)
        q[names[name]].update(x=round(ex + 3.5 + col * 1.45, 3), y=round(centre_y - 1.45 + row * 1.45, 3))
    for im in doc['images']:
        if im['image'].endswith('the_bumblezone_logo_large.png'):
            im.update(x=-8.5, y=round(centre_y + 0.4, 3), width=4.0, height=1.48)
        elif im['image'].endswith('bee_queen.png'):
            im.update(x=round(start_x, 3), y=round(centre_y + 2.0, 3), width=1.0, height=1.0)
        else:
            im.update(x=round(ex, 3), y=round(centre_y + 2.0, 3), width=0.8, height=0.8)
    for index, a in enumerate(doc['quests']):
        for b in doc['quests'][index + 1:]:
            assert abs(a['x'] - b['x']) >= 1.08 or abs(a['y'] - b['y']) >= 1.08, (a['title'], b['title'])
    for node, original in zip(doc['quests'], old['quests']):
        assert {k: v for k, v in node.items() if k not in ['x', 'y']} == {k: v for k, v in original.items() if k not in ['x', 'y']}
    assert doc['quest_enhance_decorative_lines'] == old['quest_enhance_decorative_lines']
    return (s.g.snbt(doc) + '\n').encode()


def main():
    manifest = ROOT / 'clients/cmi-expedition/evidence/overlay-files.json'
    with (manifest.parent / '.overlay-files.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        before, writes = {}, {}
        for root in ['clients/cmi-expedition/instance', 'clients/cmi-expedition/overlay', 'servers/cmi-expedition/instance']:
            path = ROOT / root / 'config/ftbquests/quests/chapters' / c.m.NAME
            before[path] = path.read_bytes()
            writes[path] = build(before[path])
        assert len(set(writes.values())) == 1
        before[manifest] = manifest.read_bytes()
        merged = json.loads(before[manifest])
        merged['config/ftbquests/quests/chapters/' + c.m.NAME] = s.sha(next(iter(writes.values())))
        writes[manifest] = (json.dumps(merged, ensure_ascii=False, indent=2) + '\n').encode()
        backup = OUT / 'backups' / ('natural-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        for path, blob in before.items():
            assert path.read_bytes() == blob
            s.atomic(backup / path.relative_to(ROOT), blob)
        for path, blob in writes.items():
            assert path.read_bytes() == before[path]
            s.atomic(path, blob)
            assert path.read_bytes() == blob
        report = {'applied': True, 'quests': 65, 'upperLayout': 'Directed graph layers with parent and child barycentres', 'allTaskBodiesPreserved': True, 'allRelationshipObjectsPreserved': True, 'threeRootsIdentical': True, 'cardOverlaps': 0, 'backupRoot': str(backup)}
        s.atomic(OUT / 'natural-layout-install.json', (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode())
        print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
