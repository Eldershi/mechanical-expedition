#!/usr/bin/env python3
"""Install the four Create progression drafts; dry run unless --apply is supplied.

Only the existing create_basics chapter family, its group title, overlay manifest,
and this operation's receipt may change. Existing quest/task progress IDs and the
164 original tutorial descriptions are checked before any installation writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets

ROOT = Path(__file__).resolve().parents[2]
GROUP_ID = '6977257A15C2F0DE'
LEGACY_NAMES = frozenset('create_basics_' + name + '.snbt' for name in (
    'orientation', 'motion', 'create_processing', 'create_logistics', 'create_fluids',
    'structures', 'redstone', 'create_packages', 'create_trains', 'information', 'create_equipment'))
TARGET_NAMES = frozenset('create_basics_' + name + '.snbt' for name in (
    'orientation', 'create_logistics', 'structures', 'create_trains'))
EXPECTED_QUESTS = 164
PREFIX = 'config/ftbquests/quests/'
HEX = re.compile(r'[0-9a-fA-F]{16}\Z')
KIND = 'create-progression-reorganization-v1'
spec = importlib.util.spec_from_file_location('create_progression_snbt', ROOT / 'clients/cmi-expedition/tools/ftb_snbt.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)
loads = parser.loads


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(blob):
    return hashlib.sha256(blob).hexdigest() if blob is not None else None


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def read(path):
    require(not path.is_symlink(), f'Refusing symbolic link: {path}')
    require(not path.exists() or path.is_file(), f'Expected a regular file: {path}')
    return path.read_bytes() if path.exists() else None


def atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name('.' + path.name + '.' + secrets.token_hex(8) + '.tmp')
    try:
        with temporary.open('xb') as output:
            output.write(blob)
            output.flush()
            os.fsync(output.fileno())
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write(path, blob):
    if blob is None:
        path.unlink(missing_ok=True)
    else:
        atomic(path, blob)


def nodes(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from nodes(child)
    elif isinstance(value, list):
        for child in value:
            yield from nodes(child)


def strings(value):
    if isinstance(value, dict):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from strings(child)
    elif isinstance(value, str):
        yield value


def object_ids(documents):
    return Counter(node['id'].upper() for doc in documents.values() for node in nodes(doc)
                   if isinstance(node.get('id'), str) and HEX.fullmatch(node['id']))


def quest_map(documents):
    result = {}
    for name, doc in documents.items():
        require(isinstance(doc, dict), f'Expected SNBT compound: {name}')
        quests = doc.get('quests', [])
        require(isinstance(quests, list), f'Expected quests list: {name}')
        for quest in quests:
            require(isinstance(quest, dict) and isinstance(quest.get('id'), str) and HEX.fullmatch(quest['id']),
                    f'Invalid quest ID in {name}')
            key = quest['id'].upper()
            require(key not in result, f'Duplicate quest ID: {key}')
            result[key] = quest
    return result


def validate_graph(documents, label):
    identifiers = object_ids(documents)
    duplicate = next((key for key, count in identifiers.items() if count != 1), None)
    require(not duplicate, f'Duplicate global object ID in {label}: {duplicate}')
    quests = quest_map(documents)
    for key, quest in quests.items():
        for field in ('tasks', 'rewards'):
            values = quest.get(field, [])
            require(isinstance(values, list), f'Invalid {field} list: {key}')
            for value in values:
                require(isinstance(value, dict) and isinstance(value.get('id'), str) and HEX.fullmatch(value['id']),
                        f'Invalid {field} object ID: {key}')
    for name, doc in documents.items():
        if not name.startswith('chapters/'):
            continue
        require(isinstance(doc.get('id'), str) and HEX.fullmatch(doc['id']), f'Invalid chapter ID: {name}')
        links = doc.get('quest_links', [])
        require(isinstance(links, list), f'Invalid quest_links list: {name}')
        for link in links:
            require(isinstance(link, dict) and isinstance(link.get('id'), str) and HEX.fullmatch(link['id']),
                    f'Invalid quest link object ID: {name}')
            target = link.get('linked_quest')
            require(isinstance(target, str) and target.upper() in quests,
                    f'Missing linked_quest target in {label}/{name}: {target}')
    visiting, visited = set(), set()

    def visit(key):
        require(key not in visiting, f'Quest dependency cycle in {label}: {key}')
        if key in visited:
            return
        visiting.add(key)
        deps = quests[key].get('dependencies', [])
        require(isinstance(deps, list), f'Invalid dependencies list: {key}')
        for dep in deps:
            require(isinstance(dep, str) and dep.upper() in quests,
                    f'Missing quest dependency in {label}: {key} -> {dep}')
            visit(dep.upper())
        visiting.remove(key)
        visited.add(key)

    for key in quests:
        visit(key)
    return len(quests)


def validate_preservation(baseline, draft):
    old, new = quest_map(baseline), quest_map(draft)
    require(len(old) == EXPECTED_QUESTS, f'Expected {EXPECTED_QUESTS} original tutorial quests, found {len(old)}')
    require(old.keys() <= new.keys(), 'Original tutorial quest IDs were removed')
    paragraphs = 0
    for key, previous in old.items():
        quest = new[key]
        for field in ('tasks', 'rewards', 'icon'):
            require(quest.get(field) == previous.get(field), f'Changed original {field}: {key}')
        before, after = previous.get('description', []), quest.get('description', [])
        require(isinstance(before, list) and isinstance(after, list) and
                all(isinstance(value, str) for value in before + after), f'Invalid description: {key}')
        require(len(after) >= len(before) and (not before or after[-len(before):] == before),
                f'Original description paragraphs changed, reordered or removed: {key}')
        paragraphs += len(before)
    for key in new.keys() - old.keys():
        quest = new[key]
        require(not quest.get('rewards'), f'New milestone must not add rewards: {key}')
        tasks = quest.get('tasks', [])
        require(isinstance(tasks, list) and tasks and all(isinstance(task, dict) and task.get('type') == 'checkmark'
                                                        for task in tasks),
                f'New milestone must contain only checkmark tasks: {key}')
    for name, doc in draft.items():
        require(doc.get('id') == baseline[name].get('id'), f'Existing chapter ID must stay stable: {name}')
        require(doc.get('group') == GROUP_ID, f'Unexpected chapter group: {name}')
        require(doc.get('filename', Path(name).stem) == Path(name).stem, f'Wrong chapter filename field: {name}')
    retired = {doc['id'].upper() for name, doc in baseline.items() if name not in draft}
    require(set(object_ids(baseline)) - retired <= set(object_ids(draft)), 'Original task/object IDs were removed')
    return {'preservedQuestIds': len(old), 'preservedTaskIds': sum(len(q.get('tasks', [])) for q in old.values()),
            'preservedDescriptionParagraphs': paragraphs, 'newMilestoneQuests': len(new) - len(old),
            'tutorialQuestNodes': len(new)}, retired


def replace_group_title(blob, fragment):
    if fragment is None:
        return blob
    value = loads(fragment.decode('utf-8'))
    groups = value.get('chapter_groups', []) if isinstance(value, dict) else []
    require(len(groups) == 1 and groups[0].get('id') == GROUP_ID and
            set(groups[0]) == {'id', 'title'} and isinstance(groups[0]['title'], str) and groups[0]['title'].strip(),
            'Group fragment must contain only the existing Create group ID and its title')
    title = groups[0]['title']

    class GroupSpans(parser.Parser):
        def __init__(self, text):
            super().__init__(text)
            self.spans = []

        def value(self):
            self.skip()
            if self.pos >= len(self.text) or self.text[self.pos] != '{':
                return super().value()
            self.pos += 1
            result, fields = {}, {}
            while True:
                self.skip()
                require(self.pos < len(self.text), 'Unterminated group compound')
                if self.text[self.pos] == '}':
                    self.pos += 1
                    if result.get('id') == GROUP_ID:
                        require('title' in fields and isinstance(result['title'], str), 'Existing group title is missing')
                        self.spans.append(fields['title'])
                    return result
                key = self.string() if self.text[self.pos] in '\"\'' else self.token(True)
                self.skip()
                require(self.pos < len(self.text) and self.text[self.pos] == ':', 'Invalid group field')
                require(key not in result, f'Duplicate group field: {key}')
                self.pos += 1
                self.skip()
                start = self.pos
                result[key] = self.value()
                fields[key] = (start, self.pos)

    text = blob.decode('utf-8')
    parsed = GroupSpans(text)
    before = parsed.value()
    parsed.skip()
    require(parsed.pos == len(text) and len(parsed.spans) == 1, 'Expected one existing Create chapter group')
    after_expected = loads(text)
    matching = [group for group in after_expected['chapter_groups'] if group.get('id') == GROUP_ID]
    require(len(matching) == 1 and before == after_expected, 'Unexpected chapter groups structure')
    if matching[0]['title'] == title:
        return blob
    matching[0]['title'] = title
    start, end = parsed.spans[0]
    result = (text[:start] + json.dumps(title, ensure_ascii=False) + text[end:]).encode('utf-8')
    require(loads(result.decode()) == after_expected, 'Group edit changed unrelated content')
    return result


class Reorganization:
    def __init__(self, root=ROOT):
        self.root = Path(root).resolve()
        self.here = self.root / 'tools/quest-workbench'
        client = self.root / 'clients/cmi-expedition'
        self.roots = {'client': client / 'instance/config/ftbquests/quests',
                      'overlay': client / 'overlay/config/ftbquests/quests',
                      'server': self.root / 'servers/cmi-expedition/instance/config/ftbquests/quests'}
        self.draft = self.root / 'design/create-progression-draft/chapters'
        self.fragment = self.draft.parent / 'chapter_groups.fragment.snbt'
        self.manifest = client / 'evidence/overlay-files.json'
        self.authoring_receipt = client / 'evidence/create-basics-20261018/completion.json'
        self.evidence = self.here / 'evidence/create-progression-install.json'
        self.guards, self.inventories, self.changes = {}, {}, {}
        self.report = None
        self.baseline_backup = None

    def safe_path(self, path):
        path = Path(path)
        require(path.is_relative_to(self.root), f'Path outside project: {path}')
        for part in (path, *path.parents):
            require(not part.is_symlink(), f'Refusing symbolic link: {part}')
            if part == self.root:
                break
        return path

    def remember(self, path):
        path = self.safe_path(path)
        blob = read(path)
        self.guards[path] = blob
        return blob

    def inventory(self, folder):
        self.safe_path(folder)
        require(folder.is_dir(), f'Missing directory: {folder}')
        files = {p.relative_to(folder).as_posix(): p for p in sorted(folder.rglob('*.snbt'))}
        self.inventories[folder] = set(files)
        return {name: self.remember(path) for name, path in files.items()}

    def prepare(self):
        current = {label: self.inventory(root) for label, root in self.roots.items()}
        reference = current['client']
        require(reference == current['server'], 'Client/server source hashes or inventories differ')
        require(all(name in reference and reference[name] == blob for name, blob in current['overlay'].items()),
                'Overlay source hash differs from client')
        managed = {name for name in reference if name.startswith('chapters/create_basics')}
        initial = {'chapters/' + name for name in LEGACY_NAMES}
        target = {'chapters/' + name for name in TARGET_NAMES}
        require(managed in (initial, target), f'Unexpected installed Create chapter set: {sorted(managed)}')
        for label, files in current.items():
            require(all(name in files and files[name] == reference[name] for name in managed | {'chapter_groups.snbt'}),
                    f'Managed source hashes differ across three roots: {label}')
        previous_blob = self.remember(self.evidence)
        previous = json.loads(previous_blob) if previous_blob is not None else None
        if managed == initial:
            receipt_blob = self.remember(self.authoring_receipt)
            require(receipt_blob is not None, 'Original 11-chapter authoring receipt is required')
            authored = {row['path'].removeprefix(PREFIX): row['sha256'] for row in json.loads(receipt_blob)['files']}
            require(all(authored.get(name) == sha(reference[name]) for name in initial),
                    'Original tutorial source changed since its authoring receipt; merge first')
            baseline_blobs = {name: reference[name] for name in initial}
        else:
            require(isinstance(previous, dict) and previous.get('kind') == KIND and previous.get('threeRootsAndManifestMatch'),
                    'Four-chapter source requires this installer\'s verified receipt')
            require(previous.get('files') == {name: sha(reference[name]) for name in target | {'chapter_groups.snbt'}},
                    'Managed chapters/group changed since the previous progression install; merge first')
            relative_backup = previous.get('baselineBackup')
            require(isinstance(relative_backup, str) and not Path(relative_backup).is_absolute() and
                    '..' not in Path(relative_backup).parts and relative_backup.startswith('tools/quest-workbench/backups/'),
                    'Invalid original tutorial backup path')
            self.baseline_backup = self.root / relative_backup
            baseline_blobs = {name: self.remember(self.baseline_backup / self.roots['client'].relative_to(self.root) / name)
                              for name in initial}
            require(all(blob is not None and sha(blob) == previous.get('baselineSourceFiles', {}).get(name)
                        for name, blob in baseline_blobs.items()), 'Original tutorial backup hashes differ')
        drafts = self.inventory(self.draft)
        require(set(drafts) == TARGET_NAMES, f'Expected exactly the four successor draft files: {sorted(TARGET_NAMES)}')
        draft_blobs = {'chapters/' + name: blob for name, blob in drafts.items()}
        baseline = {name: loads(blob.decode('utf-8')) for name, blob in baseline_blobs.items()}
        draft_docs = {name: loads(blob.decode('utf-8')) for name, blob in draft_blobs.items()}
        validation, retired_ids = validate_preservation(baseline, draft_docs)
        source_groups = reference['chapter_groups.snbt']
        groups = replace_group_title(source_groups, self.remember(self.fragment))
        group_docs = loads(groups.decode('utf-8'))
        require(sum(group.get('id') == GROUP_ID for group in group_docs.get('chapter_groups', [])) == 1,
                'Expected exactly one existing Create chapter group')
        manifest_blob = self.remember(self.manifest)
        require(manifest_blob is not None, 'Overlay manifest is required')
        manifest = json.loads(manifest_blob)
        for name in managed | {'chapter_groups.snbt'}:
            require(manifest.get(PREFIX + name) == sha(reference[name]), f'Overlay manifest mismatch: {name}')
        for name in initial - managed:
            require(PREFIX + name not in manifest, f'Stale overlay manifest entry: {name}')
        for name in initial:
            manifest.pop(PREFIX + name, None)
        manifest.update({PREFIX + name: sha(blob) for name, blob in draft_blobs.items()})
        manifest[PREFIX + 'chapter_groups.snbt'] = sha(groups)
        self.changes[self.manifest] = encoded(manifest)
        counts = {}
        for label, root in self.roots.items():
            for name in initial:
                path = root / name
                if path not in self.guards:
                    self.remember(path)
                self.changes[path] = draft_blobs.get(name)
            self.changes[root / 'chapter_groups.snbt'] = groups
            effective = dict(reference)
            effective.update(current[label])
            for name in initial:
                effective.pop(name, None)
            effective.update(draft_blobs)
            effective['chapter_groups.snbt'] = groups
            documents = {name: loads(blob.decode('utf-8')) for name, blob in effective.items()}
            for name, doc in documents.items():
                for value in strings(doc):
                    for retired in retired_ids:
                        require(not re.search(r'(?i)(?<![0-9a-f])0*' + format(int(retired, 16), 'x') + r'(?![0-9a-f])', value),
                                f'Reference to retired chapter {retired}: {label}/{name}')
            counts[label] = validate_graph(documents, label)
        require(len(set(counts.values())) == 1, 'Effective global quest counts differ across roots')
        self.changes = {path: blob for path, blob in self.changes.items() if self.guards[path] != blob}
        self.report = {'kind': KIND, 'createdAt': datetime.now().astimezone().isoformat(), 'mode': 'dry-run',
                       **validation, 'chaptersBefore': len(managed), 'chaptersAfter': len(target),
                       'totalQuestNodes': counts['client'], 'threeRootSourceHashesMatch': True,
                       'chapterGroupsChanged': source_groups != groups,
                       'files': {**{name: sha(blob) for name, blob in draft_blobs.items()}, 'chapter_groups.snbt': sha(groups)},
                       'baselineSourceFiles': {name: sha(blob) for name, blob in baseline_blobs.items()},
                       'retiredChapterIds': sorted(retired_ids), 'removedFiles': sorted(managed - target),
                       'changes': {path.relative_to(self.root).as_posix(): {'before': sha(self.guards[path]), 'after': sha(blob)}
                                   for path, blob in self.changes.items()},
                       'checks': ['164 original quest IDs, task structures, rewards and icons preserved',
                                  'every original description paragraph retained unchanged after any prepended guidance',
                                  'four existing successor chapter IDs preserved', 'no retired chapter references',
                                  'global unique object IDs, valid quest dependency targets and no cycles',
                                  'three managed source copies and overlay manifest match before writing',
                                  'unrelated chapter bytes, player state and old steam progression untouched']}
        return self.report

    def verify(self, after=None):
        after = after or {}
        for folder, names in self.inventories.items():
            expected = set(names)
            for path, blob in after.items():
                if path.is_relative_to(folder) and path.suffix == '.snbt':
                    name = path.relative_to(folder).as_posix()
                    expected.discard(name) if blob is None else expected.add(name)
            require({p.relative_to(folder).as_posix() for p in folder.rglob('*.snbt')} == expected,
                    f'Concurrent SNBT inventory change: {folder}')
        for path, before in self.guards.items():
            self.safe_path(path)
            require(read(path) == after.get(path, before), f'Concurrent file edit: {path}')

    def apply(self):
        require(self.report is not None, 'Prepare before applying')
        self.verify()
        if not self.changes:
            return {**self.report, 'mode': 'verified', 'threeRootsAndManifestMatch': True}
        backup = self.here / 'backups' / ('create-progression-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        self.safe_path(backup)
        backup.mkdir(parents=True)
        baseline_backup = self.baseline_backup or backup
        report = {**self.report, 'mode': 'applied', 'backup': backup.relative_to(self.root).as_posix(),
                  'baselineBackup': baseline_backup.relative_to(self.root).as_posix(), 'threeRootsAndManifestMatch': True}
        changes = {**self.changes, self.evidence: encoded(report)}
        backup_paths = {self.manifest, self.evidence}
        backup_paths.update(root / 'chapter_groups.snbt' for root in self.roots.values())
        backup_paths.update(root / 'chapters' / name for root in self.roots.values() for name in LEGACY_NAMES)
        for path in sorted(backup_paths):
            blob = self.guards[path]
            if blob is not None:
                atomic(backup / path.relative_to(self.root), blob)
        atomic(backup / 'receipt.json', encoded({'originals': {path.relative_to(self.root).as_posix(): sha(self.guards[path])
                                                              for path in sorted(backup_paths)},
                                                'changes': {path.relative_to(self.root).as_posix(): sha(blob)
                                                            for path, blob in changes.items()}}))
        self.verify()
        written = []
        try:
            for path, blob in changes.items():
                self.safe_path(path)
                require(read(path) == self.guards[path], f'Concurrent file edit: {path}')
                write(path, blob)
                written.append(path)
            self.verify(changes)
        except Exception:
            conflicts = []
            for path in reversed(written):
                try:
                    self.safe_path(path)
                    current = read(path)
                except (OSError, ValueError):
                    conflicts.append(str(path))
                    continue
                if current != changes[path]:
                    conflicts.append(str(path))
                else:
                    write(path, self.guards[path])
            if conflicts:
                raise RuntimeError(f'Rollback found later edits; recover from {backup}: {conflicts}')
            raise
        return report


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--apply', action='store_true', help='Install verified drafts with scoped backups and rollback protection')
    options = arguments.parse_args()
    plan = Reorganization()
    report = plan.prepare()
    if options.apply:
        report = plan.apply()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
