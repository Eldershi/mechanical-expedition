#!/usr/bin/env python3
"""Safely merge the installed Bumblezone chapters, or update their single successor.

Dry run is the default. Existing chapters must match the last install receipt.
The script never changes chapter groups, task IDs, player data, or game state.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import secrets

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TARGET = 'chapters/bumblezone_01_exploration.snbt'
LEGACY = ('chapters/bumblezone_02_queen.snbt', 'chapters/bumblezone_03_sanctum.snbt')
MANAGED = (TARGET, *LEGACY)
CHAPTER_ID = '5BAAB2F63337EF1E'
RETIRED_IDS = {'94B407DE018F0D06', '5D6D999BA7EB3886'}
GUIDES = {'the_bumblezone:root': 'D14FC9BD1F39A243',
          'the_bumblezone:wiki': 'A9B2017B541E8C4A'}
HEX = re.compile(r'[0-9a-fA-F]{16}\Z')
spec = importlib.util.spec_from_file_location('ftb_snbt', ROOT / 'clients/cmi-expedition/tools/ftb_snbt.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
loads = parser.loads


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(blob):
    return hashlib.sha256(blob).hexdigest() if blob is not None else None


def read(path):
    require(not path.is_symlink(), f'Refusing symlink: {path}')
    return path.read_bytes() if path.exists() else None


def atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + secrets.token_hex(6) + '.tmp')
    try:
        temporary.write_bytes(blob)
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write(path, blob):
    if blob is None:
        path.unlink(missing_ok=True)
    else:
        atomic(path, blob)


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def strings(value, location=''):
    if isinstance(value, dict):
        for key, child in value.items():
            yield from strings(child, location + '.' + key)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from strings(child, location + '[' + str(index) + ']')
    elif isinstance(value, str):
        yield location, value


def object_ids(documents):
    return Counter(node['id'].upper() for data in documents.values() for node in nodes(data)
                   if isinstance(node.get('id'), str) and HEX.fullmatch(node['id']))


def validate_graph(documents, label):
    ids = object_ids(documents)
    require(all(count == 1 for count in ids.values()), f'Duplicate object IDs in {label}')
    quests = {q['id'].upper(): q for data in documents.values() for q in data.get('quests', [])}
    visiting, visited = set(), set()

    def visit(key):
        require(key not in visiting, f'Quest dependency cycle in {label}: {key}')
        if key in visited:
            return
        visiting.add(key)
        for dep in quests.get(key, {}).get('dependencies', []):
            require(isinstance(dep, str) and dep.upper() in ids,
                    f'Missing dependency in {label}: {key} -> {dep}')
            visit(dep.upper())
        visiting.remove(key)
        visited.add(key)

    for key in quests:
        visit(key)
    return len(quests)


def contains_id(value, identifiers):
    for key in identifiers:
        normalized = format(int(key, 16), 'x')
        if re.search(r'(?i)(?<![0-9a-f])0*' + normalized + r'(?![0-9a-f])', value):
            return key
    return None


def validate_chapter(old_documents, merged, inventory):
    old_quests = {q['id'].upper(): q for doc in old_documents.values() for q in doc['quests']}
    new_quests = {q['id'].upper(): q for q in merged['quests']}
    require(len(merged['quests']) == len(new_quests) == len(old_quests) == 133,
            'Expected exactly 133 unique existing quest IDs')
    require(new_quests.keys() == old_quests.keys(), 'Quest ID loss or addition')
    require(merged.get('id', '').upper() == CHAPTER_ID, 'Successor chapter ID must remain stable')
    require(merged.get('group') == old_documents[TARGET].get('group'), 'Chapter group must remain stable')
    for key, quest in new_quests.items():
        old = old_quests[key]
        for field in ('tasks', 'rewards', 'icon'):
            require(quest.get(field) == old.get(field), f'Changed {field} in existing quest {key}')
        require(not quest.get('dependencies'), f'Extra FTB prerequisite in {key}')
        require(not quest.get('rewards'), f'Duplicate native reward in {key}')
    old_ids = set(object_ids(old_documents)) - RETIRED_IDS
    require(set(object_ids({TARGET: merged})) == old_ids, 'Object/task ID loss or addition')
    advancements = {row['id']: row for row in inventory['advancements']}
    require(len(advancements) == 133 and set(GUIDES) <= advancements.keys(), 'Unexpected native inventory')
    expected = set(advancements) - set(GUIDES)
    advancement_to_quest = dict(GUIDES)
    actual = Counter()
    for quest in new_quests.values():
        for task in quest.get('tasks', []):
            if task.get('type') == 'advancement':
                advancement = task.get('advancement')
                actual[advancement] += 1
                advancement_to_quest[advancement] = quest['id'].upper()
                require(task.get('criterion', '') == '', f'Partial advancement detection: {advancement}')
    require(set(actual) == expected and all(count == 1 for count in actual.values()),
            'All 131 native gameplay advancements must be detected exactly once')
    require(all(q in new_quests for q in GUIDES.values()), 'Missing native root/wiki guide node')
    native_edges = set()
    for key, row in advancements.items():
        parent = row['source'].get('parent')
        if parent:
            require(parent in advancements, f'Missing native parent: {parent}')
            native_edges.add((advancement_to_quest[parent], advancement_to_quest[key]))
    require(len(native_edges) == 132, 'Native tree must have exactly 132 parent edges')
    canonical_refs = {'q:' + format(int(key, 16), 'x'): key for key in new_quests}
    actual_edges = []
    for line in merged.get('quest_enhance_decorative_lines', []):
        refs = line.get('nodes', [])
        require(len(refs) >= 2 and all(ref in canonical_refs for ref in refs),
                f'Invalid decorative quest reference: {refs}')
        actual_edges.extend((canonical_refs[a], canonical_refs[b]) for a, b in zip(refs, refs[1:]))
    require(len(actual_edges) == len(set(actual_edges)) == 132 and set(actual_edges) == native_edges,
            'Decorative edges must exactly match all 132 native parent edges')
    for parent, child in native_edges:
        require(isinstance(new_quests[parent].get('x'), (int, float)) and
                isinstance(new_quests[child].get('x'), (int, float)) and
                new_quests[parent]['x'] < new_quests[child]['x'],
                f'Native parent must be left of child: {parent} -> {child}')
    return {'preservedQuestIds': len(old_quests), 'nativeAdvancementTasks': len(actual),
            'nativeDecorativeEdges': len(actual_edges), 'extraFtbDependencies': 0}


class Migration:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.here = self.root / 'tools/quest-workbench'
        client = self.root / 'clients/cmi-expedition'
        self.roots = {'client': client / 'instance/config/ftbquests/quests',
                      'overlay': client / 'overlay/config/ftbquests/quests',
                      'server': self.root / 'servers/cmi-expedition/instance/config/ftbquests/quests'}
        self.evidence = self.here / 'evidence/bumblezone-integration/install.json'
        self.manifest = client / 'evidence/overlay-files.json'
        self.draft = self.root / 'design/bumblezone-quest-draft/chapters'
        self.inventory = self.root / 'design/bumblezone-quest-research/inventory.json'
        self.guards = {}
        self.inventories = {}
        self.changes = {}
        self.report = None

    def remember(self, path):
        blob = read(path)
        self.guards[path] = blob
        return blob

    def prepare(self):
        previous_blob = self.remember(self.evidence)
        require(previous_blob is not None, 'Verified previous installation receipt required')
        previous = json.loads(previous_blob)
        require(previous.get('threeRootsIdentical') is True, 'Previous install was not verified')
        previous_files = previous.get('files', {})
        previous_chapters = {name for name in previous_files if name.startswith('chapters/')}
        require(previous_chapters in ({TARGET}, set(MANAGED)), 'Unexpected previous managed chapter set')
        self.inventories[self.draft] = {p.relative_to(self.draft).as_posix() for p in self.draft.rglob('*.snbt')}
        require(self.inventories[self.draft] == {Path(TARGET).name}, 'Generate exactly one successor draft chapter')
        draft_blob = self.remember(self.draft / Path(TARGET).name)
        merged = loads(draft_blob.decode())
        inventory = json.loads(self.remember(self.inventory))
        documents = {}
        for label, quest_root in self.roots.items():
            files = {p.relative_to(quest_root).as_posix(): p for p in quest_root.rglob('*.snbt')}
            self.inventories[quest_root] = set(files)
            documents[label] = {name: loads(self.remember(path).decode()) for name, path in files.items()}
            for relative in MANAGED:
                old = self.remember(quest_root / relative)
                expected_hash = previous_files.get(relative)
                require(sha(old) == expected_hash and (old is not None) == (relative in previous_chapters),
                        f'Chapter changed since previous install; merge first: {quest_root / relative}')
                self.changes[quest_root / relative] = draft_blob if relative == TARGET else None
            require('chapter_groups.snbt' in documents[label], f'Missing chapter groups in {label}')
            old_managed = {name: documents[label][name] for name in previous_chapters}
            validation = validate_chapter(old_managed, merged, inventory)
        manifest_before = self.remember(self.manifest)
        manifest = json.loads(manifest_before)
        prefix = 'config/ftbquests/quests/'
        for relative in MANAGED:
            key = prefix + relative
            if relative in previous_chapters:
                require(manifest.get(key) == previous_files[relative], f'Overlay manifest changed: {relative}')
            else:
                require(key not in manifest, f'Obsolete overlay manifest entry: {relative}')
            manifest.pop(key, None)
        manifest[prefix + TARGET] = sha(draft_blob)
        self.changes[self.manifest] = json_bytes(manifest)
        source_groups = self.guards[self.roots['client'] / 'chapter_groups.snbt']
        totals = {}
        for label in self.roots:
            combined = dict(documents['client']) if label == 'overlay' else {}
            combined.update(documents[label])
            for relative in MANAGED:
                combined.pop(relative, None)
            combined[TARGET] = merged
            for name, doc in combined.items():
                for location, value in strings(doc):
                    referenced = contains_id(value, RETIRED_IDS)
                    require(not referenced, f'Reference to retired chapter {referenced}: {label}/{name}{location}')
            totals[label] = validate_graph(combined, label)
        require(len(set(totals.values())) == 1, 'Effective quest totals differ between source/overlay/server')
        self.changes = {path: blob for path, blob in self.changes.items() if self.guards[path] != blob}
        self.report = {'createdAt': datetime.now().astimezone().isoformat(),
                       'mode': 'single-update-dry-run' if previous_chapters == {TARGET} else 'single-migration-dry-run',
                       'chaptersAdded': 1, 'questNodesAdded': 133, 'totalQuestNodes': totals['client'],
                       **validation, 'retiredChapterIds': sorted(RETIRED_IDS),
                       'removedFiles': list(LEGACY), 'chapterGroupsUnchanged': True,
                       'files': {TARGET: sha(draft_blob), 'chapter_groups.snbt': sha(source_groups)},
                       'previousFiles': previous_files, 'filesToWriteOrDelete': len(self.changes),
                       'changes': {str(path.relative_to(self.root)): {'before': sha(self.guards[path]), 'after': sha(blob)}
                                   for path, blob in self.changes.items()},
                       'checks': ['all prior managed chapter hashes and overlay entries match installation receipt',
                                  'all 133 quest IDs, task structures, rewards and icons preserved',
                                  'all 131 whole native advancements exactly once', 'zero extra FTB prerequisites',
                                  '132 exact native decorative edges, each parent left of child',
                                  'unique global object IDs and acyclic existing dependencies',
                                  'no remaining references to retired chapter IDs',
                                  'chapter groups and unrelated quest files unchanged']}
        return self.report

    def verify(self, after=None):
        after = after or {}
        for folder, original_names in self.inventories.items():
            expected_names = set(original_names)
            for path, blob in after.items():
                if path.is_relative_to(folder) and path.suffix == '.snbt':
                    name = path.relative_to(folder).as_posix()
                    if blob is None:
                        expected_names.discard(name)
                    else:
                        expected_names.add(name)
            current_names = {p.relative_to(folder).as_posix() for p in folder.rglob('*.snbt')}
            require(current_names == expected_names, f'Quest inventory changed concurrently: {folder}')
        for path, original in self.guards.items():
            require(read(path) == after.get(path, original), f'Concurrent file edit: {path}')

    def apply(self):
        require(self.report is not None, 'Prepare migration before applying')
        self.verify()
        if not self.changes:
            return {**self.report, 'mode': 'verified-single', 'threeRootsIdentical': True}
        backup = self.here / 'backups' / ('bumblezone-single-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        backup.mkdir(parents=True)
        report = {**self.report, 'mode': self.report['mode'].removesuffix('-dry-run'),
                  'backup': str(backup), 'threeRootsIdentical': True}
        changes = {**self.changes, self.evidence: json_bytes(report)}
        backup_paths = set(changes) | {root / 'chapter_groups.snbt' for root in self.roots.values()}
        receipt = {'createdAt': datetime.now().astimezone().isoformat(),
                   'originals': {str(path.relative_to(self.root)): sha(self.guards[path]) for path in sorted(backup_paths)},
                   'changes': {str(path.relative_to(self.root)): sha(blob) for path, blob in changes.items()}}
        for path in sorted(backup_paths):
            old = self.guards[path]
            if old is not None:
                atomic(backup / path.relative_to(self.root), old)
        atomic(backup / 'previous-install.json', self.guards[self.evidence])
        atomic(backup / 'receipt.json', json_bytes(receipt))
        self.verify()
        written = []
        try:
            for path, blob in changes.items():
                require(read(path) == self.guards[path], f'Concurrent file edit: {path}')
                write(path, blob)
                written.append(path)
            self.verify(changes)
        except Exception:
            conflicts = []
            for path in reversed(written):
                if read(path) != changes[path]:
                    conflicts.append(str(path))
                else:
                    write(path, self.guards[path])
            if conflicts:
                raise RuntimeError('Rollback found subsequent edits; recover from ' + str(backup) + ': ' + ', '.join(conflicts))
            raise
        atomic(backup / 'result.json', json_bytes(report))
        return report


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument('--apply', action='store_true', help='Apply the verified migration with a complete backup')
    args.add_argument('--update', action='store_true', help='Accepted for compatibility; previous receipt is always required')
    options = args.parse_args()
    migration = Migration()
    report = migration.prepare()
    if options.apply:
        report = migration.apply()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
