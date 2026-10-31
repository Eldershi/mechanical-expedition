"""Lay out researched chapters on one left-to-right axis without adding gates."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import heapq
import uuid


STEP = 2.5
ANCHOR_PREFIX = 'quest_enhance:decorative_anchor:'
ANCHOR_NAMESPACE = uuid.UUID('ac3a5704-964d-5a88-967b-d873360336e4')


def node_key(kind, obj):
    return f'{kind}:{int(obj["id"], 16):x}'


def anchor_key(image):
    click = image.get('click', '')
    return 'a:' + click[len(ANCHOR_PREFIX):] if click.startswith(ANCHOR_PREFIX) else None


def logical_lines(chapter):
    """Collapse layout-only anchors back to the original quest relationships."""
    anchors = {key for image in chapter.get('images', []) if (key := anchor_key(image))}
    outgoing = defaultdict(list)
    for line in chapter.get('quest_enhance_decorative_lines', []):
        refs = line.get('nodes', [])
        if len(refs) != 2:
            raise ValueError('Research relationships must have two endpoints')
        outgoing[refs[0]].append(refs[1])
    result = []
    for source, targets in outgoing.items():
        if source in anchors:
            continue
        for target in targets:
            visited = set()
            while target in anchors:
                if target in visited or len(outgoing[target]) != 1:
                    raise ValueError('Ambiguous or cyclic layout anchor')
                visited.add(target)
                target = outgoing[target][0]
            result.append({'nodes': [source, target]})
    return result


def horizontal_layout(chapter):
    """Keep all quest/link content, sorting the display by its existing edges."""
    objects = {node_key(kind, obj): obj
               for kind, field in [('q', 'quests'), ('l', 'quest_links')]
               for obj in chapter.get(field, [])}
    ranks = {node_key('q', obj): index
             for index, obj in enumerate(chapter.get('quests', []))}
    successors = {key: set() for key in objects}
    indegree = dict.fromkeys(objects, 0)
    relationships = logical_lines(chapter)
    for line in relationships:
        refs = line.get('nodes', [])
        for source, target in zip(refs, refs[1:]):
            if source not in objects or target not in objects:
                raise ValueError(f'Unknown line endpoint in {chapter["title"]}: {source}/{target}')
            if target not in successors[source]:
                successors[source].add(target)
                indegree[target] += 1
    for index, obj in enumerate(chapter.get('quest_links', [])):
        key = node_key('l', obj)
        ranks[key] = min((ranks[v] - 0.5 for v in successors[key] if v in ranks),
                         default=len(ranks) + index)
    ready = [(ranks[key], key) for key, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    ordered = []
    while ready:
        _, key = heapq.heappop(ready)
        ordered.append(key)
        for target in sorted(successors[key]):
            indegree[target] -= 1
            if indegree[target] == 0:
                heapq.heappush(ready, (ranks[target], target))
    if len(ordered) != len(objects):
        raise ValueError(f'Cannot make cyclic relationships run left to right: {chapter["title"]}')
    for index, key in enumerate(ordered):
        objects[key]['x'] = index * STEP
        objects[key]['y'] = 0.0
    for source, targets in successors.items():
        for target in targets:
            assert objects[source]['x'] < objects[target]['x']
    # Native Quest Enhance has straight segments, so route nonadjacent edges
    # through two zero-area image anchors above the single row of task icons.
    images = [deepcopy(image) for image in chapter.get('images', []) if not anchor_key(image)]
    lines = []
    lanes = []
    long_edges = sorted((line for line in relationships
                         if objects[line['nodes'][1]]['x'] - objects[line['nodes'][0]]['x'] > STEP),
                        key=lambda line: (objects[line['nodes'][0]]['x'], objects[line['nodes'][1]]['x']))
    routed = {}
    for line in long_edges:
        source, target = line['nodes']
        x1, x2 = objects[source]['x'], objects[target]['x']
        lane = next((i for i, end in enumerate(lanes) if end < x1), len(lanes))
        if lane == len(lanes):
            lanes.append(x2)
        else:
            lanes[lane] = x2
        y = -1.5 - lane * 0.5
        refs = []
        for side, x in [('source', x1), ('target', x2)]:
            uid = str(uuid.uuid5(ANCHOR_NAMESPACE, f'{chapter["id"]}/{source}/{target}/{side}'))
            images.append({'x': x, 'y': y, 'width': 0.0, 'height': 0.0,
                           'rotation': 0.0, 'image': 'quest_enhance:textures/icons/decorative_anchor.png',
                           'click': ANCHOR_PREFIX + uid, 'dev': False,
                           'quest_enhance_exclude_from_box_selection': True})
            refs.append('a:' + uid)
        routed[(source, target)] = [source, *refs, target]
    for line in relationships:
        source, target = line['nodes']
        refs = routed.get((source, target), [source, target])
        lines.extend({'nodes': [a, b]} for a, b in zip(refs, refs[1:]))
    if images:
        chapter['images'] = images
    else:
        chapter.pop('images', None)
    chapter['quest_enhance_decorative_lines'] = lines
    return {'objects': len(ordered), 'quests': len(chapter.get('quests', [])),
            'links': len(chapter.get('quest_links', [])), 'rows': 1,
            'step': STEP, 'width': max(0, len(ordered) - 1) * STEP,
            'logicalRelationships': len(relationships), 'routedRelationships': len(routed),
            'lineSegments': len(lines), 'routingLanes': len(lanes), 'order': ordered}
