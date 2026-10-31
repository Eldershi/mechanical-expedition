#!/usr/bin/env python3
"""Reflow installed research chapters, preserving each instance's task content."""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

import install_researched_quests as install
from research_horizontal_layout import anchor_key, horizontal_layout, logical_lines


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / 'design/researched-quest-integration-20261018'
INSTANCE_ROOTS = install.INSTANCE_ROOTS + [
    'clients/cmi-expedition/tectonic-preview/instance',
    'clients/cmi-expedition/tectonic-preview-v2/instance',
]

# Keep original SNBT number types, ItemStack NBT and unknown fields. Only layout
# coordinates, routing images and decorative segments are replaced.
RENDER = r"""
const fs = require('node:fs');
const assert = require('node:assert/strict');
const SNBT = require(process.argv[1]);
const rows = JSON.parse(fs.readFileSync(0, 'utf8'));
const prefix = 'quest_enhance:decorative_anchor:';
const withoutLayout = (doc) => {
  const copy = structuredClone(doc);
  for (const field of ['quests', 'quest_links'])
    for (const obj of copy[field] || []) { delete obj.x; delete obj.y; }
  delete copy.quest_enhance_decorative_lines;
  copy.images = (copy.images || []).filter(image => !image.click?.startsWith(prefix));
  if (!copy.images.length) delete copy.images;
  return copy;
};
const output = rows.map(row => {
  const original = SNBT.parse(row.before);
  const doc = structuredClone(original);
  for (const field of ['quests', 'quest_links']) {
    const positions = new Map((row.after[field] || []).map(obj => [obj.id, obj]));
    for (const obj of doc[field] || []) {
      const position = positions.get(obj.id);
      assert.ok(position, `Missing ${field}/${obj.id}`);
      obj.x = SNBT.number(position.x, 'd');
      obj.y = SNBT.number(position.y, 'd');
    }
  }
  const images = (doc.images || []).filter(image => !image.click?.startsWith(prefix));
  for (const image of row.after.images || []) {
    if (!image.click?.startsWith(prefix)) continue;
    const anchor = {...image};
    for (const key of ['x', 'y', 'width', 'height', 'rotation'])
      anchor[key] = SNBT.number(anchor[key], 'd');
    images.push(anchor);
  }
  if (images.length) doc.images = images; else delete doc.images;
  doc.quest_enhance_decorative_lines = row.after.quest_enhance_decorative_lines;
  assert.deepEqual(withoutLayout(original), withoutLayout(doc), row.path);
  const text = SNBT.stringify(doc) + '\n';
  assert.equal(SNBT.stringify(SNBT.parse(text)) + '\n', text, `Typed SNBT roundtrip: ${row.path}`);
  return text;
});
process.stdout.write(JSON.stringify(output));
"""


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def semantic_content(chapter):
    result = deepcopy(chapter)
    for field in ['quests', 'quest_links']:
        for obj in result.get(field, []):
            obj.pop('x', None)
            obj.pop('y', None)
    result['quest_enhance_decorative_lines'] = sorted(
        (tuple(line['nodes']) for line in logical_lines(chapter)))
    result['images'] = [image for image in result.get('images', []) if not anchor_key(image)]
    if not result['images']:
        result.pop('images')
    return result


def validate_geometry(chapter):
    objects = {f'{kind}:{int(obj["id"], 16):x}': obj
               for kind, field in [('q', 'quests'), ('l', 'quest_links')]
               for obj in chapter.get(field, [])}
    assert {obj['y'] for obj in objects.values()} == {0.0}
    assert len({obj['x'] for obj in objects.values()}) == len(objects)
    for line in logical_lines(chapter):
        source, target = line['nodes']
        assert objects[source]['x'] < objects[target]['x']
    positions = dict(objects)
    positions.update({anchor_key(image): image for image in chapter.get('images', []) if anchor_key(image)})
    for line in chapter['quest_enhance_decorative_lines']:
        a, b = (positions[ref] for ref in line['nodes'])
        # Every segment must avoid the open interior of any unrelated task icon.
        for obj in objects.values():
            if obj is a or obj is b:
                continue
            if a['y'] == b['y']:
                assert not (abs(obj['y'] - a['y']) < 0.5 and
                            min(a['x'], b['x']) < obj['x'] < max(a['x'], b['x']))
            elif a['x'] == b['x']:
                assert not (abs(obj['x'] - a['x']) < 0.5 and
                            min(a['y'], b['y']) < obj['y'] < max(a['y'], b['y']))
            else:
                raise AssertionError('Unexpected diagonal route')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    originals, updates, inventory, rows, records = {}, {}, {}, [], []
    for relative in INSTANCE_ROOTS:
        base = ROOT / relative / 'config/ftbquests/quests/chapters'
        if not base.is_dir():
            continue
        inventory[base] = sorted(path.name for path in base.glob('research_*.snbt'))
        for name in inventory[base]:
            path = base / name
            assert not path.is_symlink(), path
            raw = path.read_bytes()
            before = install.SNBT.loads(raw.decode())
            after = deepcopy(before)
            layout = horizontal_layout(after)
            validate_geometry(after)
            assert semantic_content(before) == semantic_content(after), path
            again = deepcopy(after)
            horizontal_layout(again)
            assert again == after, f'Non-idempotent layout: {path}'
            originals[path] = raw
            rows.append({'path': str(path.relative_to(ROOT)), 'before': raw.decode(), 'after': after})
            records.append({'path': str(path.relative_to(ROOT)), 'chapterId': before['id'],
                            'title': before['title'], **{k: v for k, v in layout.items() if k != 'order'}})
    process = subprocess.run(['node', '-e', RENDER, str(ROOT / 'tools/quest-workbench/editor/snbt.js')],
                             input=install.json_bytes(rows), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
    if process.returncode:
        raise ValueError(process.stderr.decode()[-4000:])
    for row, text in zip(rows, json.loads(process.stdout), strict=True):
        path = ROOT / row['path']
        parsed = install.SNBT.loads(text)
        assert parsed == row['after'], path
        updates[path] = text.encode()

    # The installed preview is a generated snapshot, so it follows the current
    # client. Never recreate chapters removed concurrently from the client.
    preview = HERE / 'preview/quests/chapters'
    client = ROOT / INSTANCE_ROOTS[0] / 'config/ftbquests/quests/chapters'
    if preview.is_dir():
        for name in inventory[client]:
            path = preview / name
            if path.exists():
                originals[path] = path.read_bytes()
                updates[path] = updates[client / name]
        snapshot_path = HERE / 'root-review/preview-snapshot.json'
        if snapshot_path.exists():
            originals[snapshot_path] = snapshot_path.read_bytes()
            snapshot = json.loads(originals[snapshot_path])
            snapshot['files'] = [
                {'path': path.relative_to(preview.parent).as_posix(),
                 'sha256': digest(updates[path] if path in updates else path.read_bytes())}
                for path in sorted(preview.parent.rglob('*.snbt'))
            ]
            updates[snapshot_path] = install.json_bytes(snapshot)

    manifest_path = ROOT / 'clients/cmi-expedition/evidence/overlay-files.json'
    originals[manifest_path] = manifest_path.read_bytes()
    manifest = json.loads(originals[manifest_path])
    overlay = ROOT / 'clients/cmi-expedition/overlay'
    for path, blob in list(updates.items()):
        if path.is_relative_to(overlay):
            manifest[path.relative_to(overlay).as_posix()] = digest(blob)
    updates[manifest_path] = install.json_bytes(manifest)
    updates = {path: blob for path, blob in updates.items() if blob != originals[path]}
    report = {'applied': False, 'createdAt': datetime.now(timezone.utc).isoformat(),
              'policy': 'one horizontal row per chapter; all relationships run left to right',
              'instances': {str(path.parent.parent.parent.parent.relative_to(ROOT)): len(names)
                            for path, names in inventory.items()},
              'logicalChapters': len({row['chapterId'] for row in records}),
              'chapterCopies': len(records), 'filesToChange': len(updates),
              'questTaskIDsDescriptionsRewardsNBTUnchanged': True,
              'logicalRelationshipsUnchanged': True, 'allSegmentsAvoidTaskIcons': True,
              'chapters': records}
    if args.apply and updates:
        for base, names in inventory.items():
            assert sorted(path.name for path in base.glob('research_*.snbt')) == names, f'Concurrent inventory edit: {base}'
        for path in updates:
            assert path.read_bytes() == originals[path], f'Concurrent edit: {path}'
        backup = HERE / 'backups' / ('horizontal-layout-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
        for path in updates:
            install.atomic(backup / path.relative_to(ROOT), originals[path])
        done = []
        try:
            for path, blob in updates.items():
                assert path.read_bytes() == originals[path], f'Concurrent edit before write: {path}'
                install.atomic(path, blob)
                done.append(path)
                assert path.read_bytes() == blob
        except BaseException:
            for path in reversed(done):
                install.atomic(path, originals[path])
            raise
        report['applied'] = True
        report['backup'] = str(backup.relative_to(ROOT))
        report['files'] = [{'path': str(path.relative_to(ROOT)), 'beforeSHA256': digest(originals[path]),
                            'afterSHA256': digest(blob)} for path, blob in updates.items()]
    report_name = 'horizontal-layout-result.json' if args.apply else 'horizontal-layout-plan.json'
    install.atomic(HERE / 'root-review' / report_name, install.json_bytes(report))
    print(json.dumps({key: value for key, value in report.items() if key not in ('chapters', 'files')},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
