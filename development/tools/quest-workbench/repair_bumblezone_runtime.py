#!/usr/bin/env python3
"""Repair stale native-parent display references, retaining live quest/task IDs."""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('bumble_import', HERE/'import_bumblezone.py')
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
loads = gen.parser()
REL = 'chapters/' + gen.FILENAME
EVIDENCE = HERE/'evidence/bumblezone-line-fix-20261018'

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.bumble-repair.tmp')
    try:
        tmp.write_bytes(blob)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

def validate(old, new, inventory):
    before, after = gen.native_node_map(old), gen.native_node_map(new)
    assert set(before) == set(after) == {row['id'] for row in inventory['advancements']}
    for key, node in after.items():
        original = before[key]
        for field in ('id', 'tasks', 'icon', 'rewards'):
            assert node.get(field, []) == original.get(field, []), (key, field)
        assert not node.get('dependencies')
        for obj in [node, *node['tasks']]:
            assert 1 < int(obj['id'], 16) <= 0x7FFFFFFFFFFFFFFF
        assert not any('自动检测' in t or '图标物品' in t or 'FTB' in t or '原生进度' in t
                       for t in node.get('description', []))
    expected = {(gen.decorative_ref(after[row['source']['parent']]['id']),
                 gen.decorative_ref(after[row['id']]['id']))
                for row in inventory['advancements'] if row['source'].get('parent')}
    actual = [tuple(line['nodes']) for line in new['quest_enhance_decorative_lines']]
    assert len(expected) == len(actual) == 132 and set(actual) == expected
    ids = {gen.decorative_ref(q['id']) for q in new['quests']}
    assert all(set(line) <= ids for line in actual)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply', action='store_true')
    args = ap.parse_args()
    targets = [r/REL for r in gen.SOURCE_ROOTS]
    old_bytes = {p: p.read_bytes() for p in targets}
    master = loads(old_bytes[targets[0]].decode())
    files, report = gen.generate(gen.DEFAULT_INVENTORY)
    rendered = files[REL].encode()
    updated = loads(rendered.decode())
    inventory = json.loads(gen.DEFAULT_INVENTORY.read_text())
    validate(master, updated, inventory)
    # Other copies can still contain the pre-runtime IDs. Require the same exact
    # native targets before replacing them with the identity of the live client.
    for path, blob in old_bytes.items():
        assert set(gen.native_node_map(loads(blob.decode()))) == set(gen.native_node_map(master)), str(path)
    manifest_path = ROOT/'clients/cmi-expedition/evidence/overlay-files.json'
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    key = 'config/ftbquests/quests/' + REL
    assert isinstance(manifest, dict) and key in manifest
    manifest[key] = sha(rendered)
    manifest_new = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode()
    plan = {'at': datetime.now().astimezone().isoformat(), 'applied': False,
            'questIDsAndTaskIDsRetainedFromLiveClient': True,
            'quests': 133, 'advancementTasks': 131, 'displayLines': 132,
            'ftbDependencies': 0, 'playerDataWritten': False,
            'before': {str(p.relative_to(ROOT)): sha(b) for p,b in old_bytes.items()},
            'afterSHA256': sha(rendered), 'manifestBeforeSHA256': sha(manifest_raw)}
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    atomic(EVIDENCE/'repair-plan.json', (json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode())
    if args.apply:
        backup = EVIDENCE/('backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        originals = {**old_bytes, manifest_path: manifest_raw}
        writes = {**{p:rendered for p in targets}, manifest_path:manifest_new}
        for p,b in originals.items():
            atomic(backup/p.relative_to(ROOT),b)
        done = []
        try:
            for p,b in writes.items():
                assert p.read_bytes() == originals[p], 'Concurrent edit: '+str(p)
                atomic(p,b)
                done.append(p)
                assert p.read_bytes() == b
            for p in targets:
                validate(master, loads(p.read_text()), inventory)
        except BaseException:
            for p in reversed(done):
                atomic(p, originals[p])
            raise
        plan.update(applied=True, backup=str(backup), allThreeCopiesIdentical=True)
        atomic(EVIDENCE/'repair-result.json', (json.dumps(plan,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps(plan, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
