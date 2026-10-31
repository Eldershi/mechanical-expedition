#!/usr/bin/env python3
"""Install legacy drafts, or dispatch single-map drafts to the guarded migration."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import runpy
import secrets
import zipfile

ROOT = Path(__file__).resolve().parents[2]
WORKBENCH = Path(__file__).resolve().parent
DRAFT = ROOT / 'design/bumblezone-quest-draft'
CLIENT = ROOT / 'clients/cmi-expedition'
ROOTS = {
    'client': CLIENT / 'instance/config/ftbquests/quests',
    'overlay': CLIENT / 'overlay/config/ftbquests/quests',
    'server': ROOT / 'servers/cmi-expedition/instance/config/ftbquests/quests',
}
spec = importlib.util.spec_from_file_location('ftb_snbt', CLIENT / 'tools/ftb_snbt.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
loads = parser.loads


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def read(path):
    assert not path.is_symlink(), f'Refusing symlink: {path}'
    return path.read_bytes() if path.exists() else None


def atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        temporary.write_bytes(blob)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def validate(chapters, groups):
    current = {p.relative_to(ROOTS['client']).as_posix(): loads(p.read_text())
               for p in ROOTS['client'].rglob('*.snbt')}
    current.update({name: loads(blob.decode()) for name, blob in chapters.items()})
    current['chapter_groups.snbt'] = loads(groups.decode())
    ids = Counter(n['id'].upper() for data in current.values() for n in nodes(data)
                  if isinstance(n.get('id'), str) and re.fullmatch('[0-9a-fA-F]{16}', n['id']))
    assert all(count == 1 for count in ids.values()), 'Duplicate FTB object ID'
    quests = [q for data in current.values() for q in data.get('quests', [])]
    by_id = {q['id'].upper(): q for q in quests}
    visiting, visited = set(), set()

    def visit(key):
        assert key not in visiting, f'Cyclic quest dependency: {key}'
        if key in visited:
            return
        visiting.add(key)
        for dep in by_id.get(key, {}).get('dependencies', []):
            assert dep.upper() in ids, f'Missing dependency: {dep}'
            visit(dep.upper())
        visiting.remove(key)
        visited.add(key)

    for key in by_id:
        visit(key)
    inventory = json.loads((ROOT / 'design/bumblezone-quest-research/inventory.json').read_text())
    expected = {a['id'] for a in inventory['advancements']
                if a['id'] not in ('the_bumblezone:root', 'the_bumblezone:wiki')}
    additions = [q for blob in chapters.values() for q in loads(blob.decode()).get('quests', [])]
    advancement_tasks = [t for q in additions for t in q.get('tasks', []) if t.get('type') == 'advancement']
    actual = Counter(t.get('advancement') for t in advancement_tasks)
    assert set(actual) == expected and all(n == 1 for n in actual.values()), 'Native progress coverage mismatch'
    assert all(t.get('criterion', '') == '' for t in advancement_tasks), 'Must detect entire advancement'
    assert all(not q.get('rewards') for q in additions), 'Native rewards must not be duplicated'
    jars = list((CLIENT / 'instance/mods').glob('the_bumblezone-*.jar'))
    assert len(jars) == 1
    with zipfile.ZipFile(jars[0]) as jar:
        for advancement in actual:
            namespace, path = advancement.split(':', 1)
            assert f'data/{namespace}/advancements/{path}.json' in jar.namelist(), advancement
    return {'chaptersAdded': len(chapters), 'questNodesAdded': len(additions),
            'nativeAdvancementTasks': len(advancement_tasks), 'totalQuestNodes': len(quests),
            'checks': ['SNBT parse', 'unique IDs', 'existing dependencies', 'acyclic graph',
                       'all 131 installed gameplay advancements exactly once', 'whole advancement detection',
                       'no duplicate native rewards']}


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--apply', action='store_true')
    args.add_argument('--update', action='store_true',
                      help='Replace only chapters whose current hashes match the previous installation receipt')
    options = args.parse_args()
    # The single-map successor also retires the two legacy files. Its migration
    # validates the prior receipt and preserves all quest/task IDs before doing so.
    draft_chapters = sorted((DRAFT / 'chapters').glob('*.snbt'))
    if [p.name for p in draft_chapters] == ['bumblezone_01_exploration.snbt']:
        runpy.run_path(str(WORKBENCH / 'migrate_bumblezone_single.py'), run_name='__main__')
        return
    evidence = WORKBENCH / 'evidence/bumblezone-integration/install.json'
    previous_receipt = read(evidence)
    previous = json.loads(previous_receipt) if options.update and previous_receipt else None
    if options.update:
        assert isinstance(previous, dict) and previous.get('threeRootsIdentical'), 'Verified previous install receipt required'
    chapters = {'chapters/' + p.name: p.read_bytes() for p in draft_chapters}
    assert len(chapters) == 3, 'Generate all three draft chapters first'
    fragment = loads((DRAFT / 'chapter_groups.fragment.snbt').read_text())
    new_groups = fragment['chapter_groups']
    assert len(new_groups) == 1
    group = new_groups[0]
    source_groups = read(ROOTS['client'] / 'chapter_groups.snbt')
    group_data = loads(source_groups.decode())
    existing = next((g for g in group_data['chapter_groups'] if g['id'] == group['id']), None)
    if existing:
        assert existing == group, 'Existing group ID has different contents'
        groups = source_groups
    else:
        text = source_groups.decode()
        newline = '\r\n' if '\r\n' in text else '\n'
        marker = '\t]' + newline
        assert text.count(marker) == 1, 'Unexpected chapter_groups layout; merge manually'
        line = '\t\t{ id: ' + json.dumps(group['id']) + ', title: ' + json.dumps(group['title'], ensure_ascii=False) + ' }' + newline
        groups = text.replace(marker, line + marker).encode()
    report = validate(chapters, groups)
    changes = {**chapters, 'chapter_groups.snbt': groups}
    originals = {}
    for key, root in ROOTS.items():
        for relative, blob in changes.items():
            path = root / relative
            old = read(path)
            if relative != 'chapter_groups.snbt':
                if options.update:
                    assert old is not None and sha(old) == previous['files'].get(relative), f'Chapter changed since previous install; merge first: {path}'
                else:
                    assert old is None or old == blob, f'Existing edited chapter needs merge: {path}'
            else:
                assert old is None or old in (source_groups, groups), f'Independent group edit: {path}'
            originals[path] = old
    manifest_path = CLIENT / 'evidence/overlay-files.json'
    manifest_before = read(manifest_path)
    manifest = json.loads(manifest_before)
    if options.update:
        for relative in chapters:
            assert manifest.get('config/ftbquests/quests/' + relative) == previous['files'].get(relative), f'Overlay manifest changed for {relative}'
    for relative, blob in changes.items():
        manifest['config/ftbquests/quests/' + relative] = sha(blob)
    manifest_after = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    originals[manifest_path] = manifest_before
    planned = {root / relative: blob for root in ROOTS.values() for relative, blob in changes.items()}
    planned[manifest_path] = manifest_after
    planned = {path: blob for path, blob in planned.items() if originals[path] != blob}
    report.update({'mode': 'apply' if options.apply else 'dry-run', 'filesToWrite': len(planned),
                   'files': {relative: sha(blob) for relative, blob in changes.items()}})
    if options.update:
        report['mode'] = 'update' if options.apply else 'update-dry-run'
        report['previousFiles'] = previous['files']
    if options.apply and planned:
        backup = WORKBENCH / 'backups' / ('bumblezone-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        if previous_receipt is not None:
            atomic(backup / 'previous-install.json', previous_receipt)
        receipt = {'createdAt': datetime.now().astimezone().isoformat(), 'originals': {}}
        for path in planned:
            relative = path.relative_to(ROOT)
            old = originals[path]
            receipt['originals'][str(relative)] = sha(old) if old is not None else None
            if old is not None:
                atomic(backup / relative, old)
        atomic(backup / 'receipt.json', (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode())
        for path, old in originals.items():
            assert read(path) == old, f'File changed while preparing import: {path}'
        written = []
        try:
            for path, blob in planned.items():
                assert read(path) == originals[path], f'Concurrent edit: {path}'
                atomic(path, blob)
                written.append(path)
        except Exception:
            for path in reversed(written):
                old = originals[path]
                if old is None:
                    path.unlink(missing_ok=True)
                else:
                    atomic(path, old)
            raise
        report['backup'] = str(backup)
    if options.apply:
        for root in ROOTS.values():
            assert all(read(root / relative) == blob for relative, blob in changes.items())
        report['threeRootsIdentical'] = True
        evidence.parent.mkdir(parents=True, exist_ok=True)
        # Preserve the original apply receipt when rerun only verifies the install.
        if planned or not evidence.exists():
            atomic(evidence, (json.dumps(report, ensure_ascii=False, indent=2) + '\n').encode())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
