#!/usr/bin/env python3
"""Install reviewed coordinate-only adventure layouts with byte backups."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('layout_surgery', ROOT/'design/quest-name-display-fix-20261018/apply_names.py')
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
TOKEN = n.s.TOKEN


def enclosing(text, offset):
    stack = []
    for token in TOKEN.finditer(text):
        if token.start() >= offset:
            break
        if token.group() == '{':
            stack.append(token.start())
        elif token.group() == '}':
            stack.pop()
    start = stack[-1]
    depth = 0
    for token in TOKEN.finditer(text, start):
        if token.group() == '{':
            depth += 1
        elif token.group() == '}':
            depth -= 1
            if not depth:
                return start, token.end()
    raise AssertionError('Unclosed coordinate object')


def replace_xy(text, selector, xy):
    hits = list(re.finditer(selector, text))
    assert len(hits) == 1, (selector, len(hits))
    a, b = enclosing(text, hits[0].start())
    block = text[a:b]
    for field in ('x', 'y'):
        pattern = re.compile(r'(?m)^(\t+'+field+r':\s*)(-?\d+(?:\.\d+)?)([dDfF]?)(\s*)$')
        matches = list(pattern.finditer(block))
        assert len(matches) == 1, (selector, field, len(matches))
        m = matches[0]
        value = float(xy[field])
        assert abs(value) < 100
        literal = str(round(value, 6)) + m[3]
        block = block[:m.start(2)] + literal + block[m.end(3):]
    return text[:a] + block + text[b:]


def normalized(chapter):
    copy = deepcopy(chapter)
    for key in ('quests', 'quest_links', 'images'):
        for node in copy.get(key, []):
            node.pop('x', None)
            node.pop('y', None)
    return copy


def positions(c):
    return [{'id': q.get('questId', q.get('id')), 'xy': q.get('new', {'x':q.get('x'), 'y':q.get('y')})}
            for q in c.get('quests', c.get('nodes', []))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--plans', nargs='+', required=True)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    chapters = []
    inputs = []
    for name in args.plans:
        path = HERE/name
        blob = path.read_bytes()
        plan = json.loads(blob)
        chapters.extend(plan['chapters'])
        inputs.append({'path': str(path.relative_to(ROOT)), 'sha256': n.sha(blob)})
    assert len({c['filename'] for c in chapters}) == len(chapters)
    before, writes, rows = {}, {}, []
    for c in chapters:
        current = n.ROOTS[0]/n.REL/c['filename']
        assert n.sha(current.read_bytes()) == c['sourceSha256'], ('Plan source changed', current)
        qs = positions(c)
        xy = {q['id']: q['xy'] for q in qs}
        assert len(xy) == len(qs)
        pairs = []
        for i, a in enumerate(qs):
            for b in qs[i+1:]:
                if abs(a['xy']['x']-b['xy']['x']) < 64/72 and abs(a['xy']['y']-b['xy']['y']) < 1:
                    pairs.append((a['id'], b['id']))
        assert not pairs, (c['filename'], 'Overlapping cards', pairs)
        for base in n.ROOTS:
            path = base/n.REL/c['filename']
            raw = path.read_bytes()
            old = n.s.loads(raw.decode())
            assert old['group'] == '54D4CAA40ADB5408'
            assert {q['id'] for q in old['quests']} == set(xy), ('Node coverage', path)
            text = raw.decode()
            for q in qs:
                text = replace_xy(text, r'\bid\s*:\s*"'+re.escape(q['id'])+'"', q['xy'])
            for link in c.get('questLinks', []):
                lid = link.get('id', link.get('linkId'))
                text = replace_xy(text, r'\bid\s*:\s*"'+re.escape(lid)+'"', link['new'])
            seen = set()
            for image in c.get('images', []):
                idx = image['index']
                assert idx not in seen
                seen.add(idx)
                im = old['images'][idx]
                identity = image.get('identity', im.get('click'))
                assert identity == im.get('click'), ('Image identity', path, idx)
                if identity:
                    selector = r'\bclick\s*:\s*'+re.escape(json.dumps(identity, ensure_ascii=False))
                else:
                    assert im.get('image')
                    selector = r'\bimage\s*:\s*'+re.escape(json.dumps(im['image'], ensure_ascii=False))
                text = replace_xy(text, selector, image['new'])
            assert seen == set(range(len(old.get('images', [])))), ('Image coverage', path, seen)
            new = n.s.loads(text)
            assert normalized(new) == normalized(old), ('Non-coordinate change', path)
            assert all({'x':q.get('x',0),'y':q.get('y',0)} == xy[q['id']] for q in new['quests'])
            before[path] = raw
            writes[path] = text.encode()
            rows.append({'path':str(path.relative_to(ROOT)), 'title':old['title'], 'quests':len(qs),
                         'beforeSha256':n.sha(raw), 'afterSha256':n.sha(writes[path]),
                         'onlyCoordinatesChanged':True})
    manifest_path = ROOT/'clients/cmi-expedition/evidence/overlay-files.json'
    before[manifest_path] = manifest_path.read_bytes()
    manifest = json.loads(before[manifest_path])
    for path, blob in writes.items():
        if n.ROOTS[1] in path.parents:
            manifest[path.relative_to(n.ROOTS[1]).as_posix()] = n.sha(blob)
    writes[manifest_path] = n.encoded(manifest)
    result = {'applied':False, 'plans':inputs, 'chapterCount':len(chapters), 'questCount':sum(len(positions(c)) for c in chapters),
              'allNonCoordinateFieldsPreserved':True, 'decorativeGraphPreserved':True,
              'allIDsTasksConditionsRewardsSubtitlesPreserved':True, 'files':rows}
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    if args.apply:
        backup = HERE/'backups'/stamp
        for path, blob in before.items():
            n.atomic(backup/path.relative_to(ROOT), blob)
        for path, blob in before.items():
            assert path.read_bytes() == blob, ('Concurrent edit', path)
        done = []
        try:
            for path, blob in writes.items():
                assert path.read_bytes() == before[path], ('Concurrent edit', path)
                n.atomic(path, blob)
                done.append(path)
                assert path.read_bytes() == blob
        except BaseException:
            for path in reversed(done):
                n.atomic(path, before[path])
            raise
        result.update(applied=True, appliedAt=datetime.now().astimezone().isoformat(), backupRoot=str(backup))
    report_name = ('install-' if args.apply else 'dry-run-') + stamp + '.json'
    n.atomic(HERE/report_name, n.encoded(result))
    print(json.dumps({k:v for k,v in result.items() if k != 'files'},ensure_ascii=False))


if __name__ == '__main__':
    main()
