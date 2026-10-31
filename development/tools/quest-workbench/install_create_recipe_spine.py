#!/usr/bin/env python3
"""Install contract-approved Create item detection drafts; dry run by default.

The historical reorganization installer supplies scoped backups, atomic writes,
concurrent-edit guards and rollback. This successor changes only its four managed
chapters, the Create topic group's title, overlay manifest and a separate receipt.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


base = module_at('create_spine_reorganization', HERE / 'reorganize_create_progression.py')
recipe_data = module_at('create_spine_recipe_data', HERE / 'recipe_data.py')
require, sha, loads = base.require, base.sha, base.loads
KIND = 'create-recipe-spine-install-v1'
MAIN = 'chapters/create_basics_orientation.snbt'
MAIN_GROUP = '050255AE19A93344'
BASELINE = 'design/create-progression-draft/source-inventory.json'
CURRENT_SNAPSHOT = 'design/create-recipe-spine-draft/source/current-chapters'
RESOURCE = re.compile(r'[a-z0-9_.-]+:[a-z0-9_./-]+\Z')
TASK_MUTABLE = {'type', 'item', 'count', 'consume_items', 'only_from_crafting', 'match_nbt', 'task_screen_only', 'title'}


def ids(value, label):
    require(isinstance(value, list) and all(isinstance(key, str) and base.HEX.fullmatch(key) for key in value),
            f'Invalid {label} ID list')
    normalized = [key.upper() for key in value]
    require(len(set(normalized)) == len(normalized), f'Duplicate {label} IDs')
    return set(normalized)


def rows_by_quest(rows, label):
    require(isinstance(rows, list), f'Invalid contract {label}')
    result = {}
    for row in rows:
        require(isinstance(row, dict), f'Invalid contract row in {label}')
        key, task = row.get('questId'), row.get('taskId')
        require(isinstance(key, str) and base.HEX.fullmatch(key) and isinstance(task, str) and base.HEX.fullmatch(task),
                f'Invalid quest/task ID in {label}')
        key = key.upper()
        require(key not in result, f'Duplicate contract quest in {label}: {key}')
        result[key] = row
    return result


def validate_item_task(task, row, label):
    require(isinstance(task, dict) and ('title' not in task or isinstance(task['title'], str)), f'Invalid item task: {label}')
    require(task.get('id') == row['taskId'] and task.get('type') == 'item', f'Item task ID/type differs from contract: {label}')
    require(task.get('item') == row.get('item'), f'Item target differs from contract: {label}')
    count = task.get('count', 1)
    require(type(count) is int and 1 <= count <= 0x7fffffffffffffff and type(row.get('count')) is int and count == row['count'],
            f'Item count must match contract and be a positive long: {label}')
    for key in ('consume_items', 'only_from_crafting'):
        require(task.get(key) is False, f'Item detection must explicitly set {key}:false: {label}')
    for key in ('match_nbt', 'task_screen_only', 'weak_nbt_match'):
        require(key not in task or task[key] is False, f'Unsupported item matching/screen restriction: {label}/{key}')
    item = task['item']
    if isinstance(item, str):
        require(RESOURCE.fullmatch(item) and item != 'minecraft:air' and not item.startswith('itemfilters:') and
                not row.get('matchTag'), f'Invalid item resource: {label}')
        return {item}
    require(isinstance(item, dict) and set(item) <= {'id', 'Count', 'tag'} and item.get('id') == 'itemfilters:tag' and
            item.get('Count', 1) == 1 and isinstance(item.get('tag'), dict) and set(item['tag']) == {'value'} and
            item['tag'].get('value') == row.get('matchTag') and isinstance(row.get('matchTag'), str) and
            RESOURCE.fullmatch(row['matchTag']), f'Only an explicitly contracted native tag filter is supported: {label}')
    members = row.get('matchedItemIds')
    require(isinstance(members, list) and members and all(isinstance(member, str) and RESOURCE.fullmatch(member) and
                                                        member != 'minecraft:air' for member in members) and
            len(set(members)) == len(members), f'Tag filter requires distinct actual matchedItemIds: {label}')
    return {'itemfilters:tag', *members}


def validate_spine(baseline, origin, draft, contract):
    old, source, new = base.quest_map(baseline), base.quest_map(origin), base.quest_map(draft)
    require(len(old) == 164 and old.keys() <= new.keys(), 'All 164 original tutorial quest IDs must survive')
    conversions = rows_by_quest(contract.get('originalTaskConversions'), 'originalTaskConversions')
    materials = rows_by_quest(contract.get('newMaterialQuests'), 'newMaterialQuests')
    allowed = contract.get('allowedTaskFieldsChanged')
    require(isinstance(allowed, list) and all(isinstance(field, str) for field in allowed) and
            len(set(allowed)) == len(allowed) and set(allowed) <= TASK_MUTABLE,
            'Contract must explicitly approve only supported original task fields')
    allowed = set(allowed)
    require(conversions.keys() <= old.keys(), 'Conversion whitelist contains a non-original tutorial')
    require(not (materials.keys() & source.keys()), 'New material IDs must not reuse old tutorial/milestone quest IDs')
    paragraphs, targets = 0, set()
    for key, previous in old.items():
        quest = new[key]
        for field in ('icon', 'rewards'):
            require(quest.get(field) == previous.get(field), f'Changed original {field}: {key}')
        before, after = previous.get('description', []), quest.get('description', [])
        require(isinstance(before, list) and isinstance(after, list) and all(isinstance(p, str) for p in before + after) and
                len(after) >= len(before) and (not before or after[-len(before):] == before),
                f'Original description suffix changed: {key}')
        paragraphs += len(before)
        previous_tasks, tasks = previous.get('tasks', []), quest.get('tasks', [])
        if key not in conversions:
            require(tasks == previous_tasks, f'Unapproved original task mutation: {key}')
            continue
        row = conversions[key]
        require(isinstance(tasks, list) and len(tasks) == len(previous_tasks), f'Changed original task list length: {key}')
        require(sum(task.get('id') == row['taskId'] for task in previous_tasks) == 1, f'Conversion task is not owned by original quest: {key}')
        for original_task, task in zip(previous_tasks, tasks):
            if original_task.get('id') != row['taskId']:
                require(task == original_task, f'Unapproved sibling task mutation: {key}')
                continue
            require(original_task.get('type') == 'checkmark', f'Only original checkmarks may become item tasks: {key}')
            require({k: v for k, v in original_task.items() if k not in allowed} ==
                    {k: v for k, v in task.items() if k not in allowed}, f'Changed protected original task fields: {key}')
            targets.update(validate_item_task(task, row, key))
    require(paragraphs == 601, f'Expected all 601 original description paragraphs, found {paragraphs}')
    source_chapter = {quest['id'].upper(): name for name, doc in origin.items() for quest in doc.get('quests', [])}
    factory = {key for key in source.keys() - old.keys() if source_chapter[key] == MAIN}
    topics = set(source) - set(old) - factory
    require(len(factory) == 10 and len(topics) == 12, 'Expected the recorded 10 factory and 12 topic milestones')
    removed = ids(contract.get('oldMilestonesRemoved'), 'oldMilestonesRemoved')
    require(removed <= factory and set(source) - set(new) == removed, 'Only contracted old factory milestones may be removed')
    require(ids(contract.get('preservedTopicMilestones'), 'preservedTopicMilestones') == topics,
            'All twelve topic milestone IDs must be declared preserved')
    for key in (factory - removed) | topics:
        require(key in new, f'Missing retained milestone: {key}')
        for field in ('tasks', 'icon', 'rewards'):
            require(new[key].get(field) == source[key].get(field), f'Changed retained milestone {field}: {key}')
        require(all(task.get('type') == 'checkmark' for task in new[key].get('tasks', [])), f'Topic milestone must remain a checkmark: {key}')
        if key in topics:
            require(any(q.get('id', '').upper() == key for q in draft[source_chapter[key]].get('quests', [])),
                    f'Topic milestone moved to a different chapter: {key}')
    require(set(new) - set(source) == set(materials), 'Every new quest must be a contracted material node')
    for key, row in materials.items():
        quest = new[key]
        require(not quest.get('rewards'), f'New material quest must not add rewards: {key}')
        require(isinstance(quest.get('tasks'), list) and len(quest['tasks']) == 1, f'New material needs one detection task: {key}')
        require(set(quest['tasks'][0]) <= TASK_MUTABLE | {'id', 'weak_nbt_match'}, f'Unknown new material task fields: {key}')
        targets.update(validate_item_task(quest['tasks'][0], row, key))
    for name, doc in draft.items():
        require(doc.get('id') == baseline[name].get('id'), f'Chapter ID changed: {name}')
        require(doc.get('filename', Path(name).stem) == Path(name).stem, f'Chapter filename changed: {name}')
        require(doc.get('group') == (MAIN_GROUP if name == MAIN else base.GROUP_ID), f'Unexpected chapter group: {name}')
    require(draft[MAIN].get('title') == '机械动力起步' and draft[MAIN].get('order_index') == 1,
            'Main chapter must be 机械动力起步 with order_index 1')
    retained_ids = set(base.object_ids(baseline)) - {doc['id'].upper() for name, doc in baseline.items() if name not in draft}
    require(retained_ids <= set(base.object_ids(draft)), 'An original chapter/task/object ID was removed')
    return {'preservedQuestIds': 164, 'preservedTaskIds': sum(len(q.get('tasks', [])) for q in old.values()),
            'preservedDescriptionParagraphs': paragraphs, 'originalTaskConversions': len(conversions),
            'preservedTopicMilestones': len(topics), 'removedFactoryMilestones': sorted(removed),
            'newMaterialQuests': len(materials), 'tutorialQuestNodes': len(new)}, targets


def validate_links_and_decorations(documents):
    quests = base.quest_map(documents)
    for name, doc in documents.items():
        if not name.startswith('chapters/'):
            continue
        local = {q['id'].upper() for q in doc.get('quests', [])}
        for link in doc.get('quest_links', []):
            target = link.get('linked_quest')
            require(isinstance(target, str) and base.HEX.fullmatch(target) and 0 < int(target, 16) <= 0x7fffffffffffffff and
                    target.upper() in quests, f'Invalid signed-63-bit quest link target: {name}/{target}')
        for line in doc.get('quest_enhance_decorative_lines', []):
            points = line.get('nodes', []) if isinstance(line, dict) else []
            require(isinstance(points, list) and len(points) >= 2, f'Invalid decorative line: {name}')
            for point in points:
                match = re.fullmatch(r'q:([0-9a-fA-F]{1,16})', point) if isinstance(point, str) else None
                require(match and match[1].upper().zfill(16) in local, f'Dangling decorative quest reference: {name}/{point}')


class Installation(base.Reorganization):
    def __init__(self, root=base.ROOT):
        super().__init__(root)
        self.draft = self.root / 'design/create-recipe-spine-draft/chapters'
        self.fragment = self.draft.parent / 'chapter_groups.fragment.snbt'
        self.contract = self.draft.parent / 'contract.json'
        self.original_inventory = self.root / BASELINE
        self.current_snapshot = self.root / CURRENT_SNAPSHOT
        self.previous_evidence = self.evidence
        self.evidence = self.here / 'evidence/create-recipe-spine-install.json'
        self.audit = self.here / 'evidence/create-recipe-spine-audit.json'

    def recipe_items(self, targets, declared):
        require(isinstance(declared, list) and len(set(declared)) == len(declared) and
                all(isinstance(item, str) and RESOURCE.fullmatch(item) and item != 'minecraft:air' for item in declared),
                'existingItemIds must be unique item resource IDs')
        require(targets <= set(declared), 'Item task target is missing from contract existingItemIds')
        marker_blob = self.remember(self.here / 'data/active-export.json')
        require(marker_blob is not None, 'A completed local RecipeIndex snapshot is required')
        marker = json.loads(marker_blob)
        require(marker.get('exitCode') == 0 and marker.get('endedAt'), 'Recipe snapshot did not complete successfully')
        export = self.safe_path(Path(marker['exportRoot']))
        require(export.is_relative_to(self.here), 'Recipe snapshot must be inside this workbench')
        for name in ('items.json', 'categories.json', 'index.json', 'manifest.json'):
            require(self.remember(export / name) is not None, f'Missing recipe snapshot file: {name}')
        require(json.loads(self.guards[export / 'manifest.json']).get('aborted') is False, 'Recipe snapshot was aborted')
        index = recipe_data.RecipeIndex(self.here)
        status = index.status()
        require(status['ready'] and not status['error'], f'RecipeIndex cannot load this snapshot: {status["error"]}')
        for item in declared:
            require(any(row['id'] == item and row['kind'] == 'item' for row in index.items('item|' + item, 100)['items']),
                    f'Item is absent from the actual RecipeIndex: {item}')
        self.recipe_index = index
        self.recipe_export = export
        return {'exportRoot': export.relative_to(self.root).as_posix(), 'exportedAt': marker['endedAt'],
                'sourceFingerprint': marker.get('sourceFingerprint'), 'checkedItemIds': len(declared),
                'itemsSha256': sha(self.guards[export / 'items.json'])}

    def tag_inputs(self, contract):
        rows = [row for field in ('originalTaskConversions', 'newMaterialQuests') for row in contract[field] if row.get('matchTag')]
        if not rows:
            return []
        audit_blob = self.remember(self.audit)
        require(audit_blob is not None, 'Native tag detection requires the current recipe audit')
        require(contract.get('auditPath') == self.audit.relative_to(self.root).as_posix() and
                contract.get('auditSha256') == sha(audit_blob), 'Contract recipe audit path/hash differs from current evidence')
        audit = json.loads(audit_blob)
        require(audit.get('schemaVersion') == 1, 'Unsupported recipe audit schema')
        index = self.recipe_index
        checked = []
        for row in rows:
            tag = row['matchTag']
            group = audit.get('tagInputGroups', {}).get(tag, {})
            options = group.get('resolvedOptions', [])
            members = set(row['matchedItemIds'])
            require(group.get('taskFilterStack') == row['item'] and group.get('optionCount') == len(options) == len(members) and
                    {option.get('id') for option in options} == members, f'Tag task differs from audited native input group: {tag}')
            recipe_id = group.get('verifiedViaRecipeId')
            require(isinstance(recipe_id, str) and (not row.get('selectedRecipeId') or row['selectedRecipeId'] == recipe_id),
                    f'Tag task selected recipe differs from audit: {tag}')
            require(any(node.get('tag') == tag for source in group.get('sources', [])
                        for ingredient in source.get('recipeJson', {}).get('ingredients', []) for node in base.nodes(ingredient)),
                    f'Tag is absent from audited recipe source ingredients: {tag}')
            outputs = [item for item, detail in audit.get('items', {}).items() if detail.get('selectedRecipeId') == recipe_id and
                       any({option.get('id') for option in slot.get('options', [])} == members for slot in detail.get('inputs', []))]
            require(outputs, f'Tag group is not a complete selected recipe input slot: {tag}')
            found = False
            for output in outputs:
                target = index._by_key.get('item|' + output)
                require(target is not None, f'Tag recipe output is absent from RecipeIndex: {output}')
                refs = index._index.get(target['k'], {}).get('p', [])
                for category_index, _ in refs:
                    path = self.safe_path((self.recipe_export / index._categories[category_index]['dir'] / 'recipes.json').resolve())
                    require(path.is_relative_to(self.recipe_export), 'Recipe category escapes export root')
                    if path not in self.guards:
                        self.remember(path)
                for offset in range(0, len(refs), 48):
                    for recipe in index.query('item|' + output, offset=offset, limit=48)['recipes']:
                        if recipe.get('id') != recipe_id or recipe.get('error'):
                            continue
                        for slot in recipe['raw'].get('in', []):
                            raw_members = {index._by_key.get(option[0], {}).get('id') for option in slot
                                           if isinstance(option, list) and option and isinstance(option[0], str)}
                            if raw_members == members:
                                found = True
                if found:
                    break
            require(found, f'Tag members differ from the actual selected RecipeIndex raw input slot: {tag}')
            checked.append({'tag': tag, 'selectedRecipeId': recipe_id, 'matchedItemIds': len(members)})
        return checked

    def prepare(self):
        current = {label: self.inventory(root) for label, root in self.roots.items()}
        reference = current['client']
        target = {'chapters/' + name for name in base.TARGET_NAMES}
        require(reference == current['server'], 'Client/server source hashes or inventories differ')
        require(all(name in reference and reference[name] == blob for name, blob in current['overlay'].items()),
                'Overlay source hash differs from client')
        require({name for name in reference if name.startswith('chapters/create_basics')} == target,
                'Expected the existing four Create progression chapters')
        for label, files in current.items():
            require(all(name in files and files[name] == reference[name] for name in target | {'chapter_groups.snbt'}),
                    f'Managed source hashes differ across three roots: {label}')
        origin_receipt = json.loads(self.remember(self.previous_evidence) or b'null')
        require(isinstance(origin_receipt, dict) and origin_receipt.get('kind') == base.KIND and
                origin_receipt.get('threeRootsAndManifestMatch'), 'Verified prior four-chapter installation receipt is required')
        previous_blob = self.remember(self.evidence)
        previous = json.loads(previous_blob) if previous_blob is not None else origin_receipt
        require(previous.get('kind') == (KIND if previous_blob is not None else base.KIND) and
                previous.get('threeRootsAndManifestMatch'), 'Invalid previous installation receipt')
        require(previous.get('files') == {name: sha(reference[name]) for name in target | {'chapter_groups.snbt'}},
                'Managed sources/group changed since previous installation; merge first')
        contract_blob = self.remember(self.contract)
        require(contract_blob is not None, 'Generate contract.json before installation')
        contract = json.loads(contract_blob)
        baseline_contract = contract.get('baseline', {})
        inventory_blob = self.remember(self.original_inventory)
        require(baseline_contract.get('path') == BASELINE and baseline_contract.get('sha256') == sha(inventory_blob),
                'Contract must identify the unchanged frozen tutorial baseline')
        inventory = json.loads(inventory_blob)
        require(set(inventory.get('chapters', {})) == base.LEGACY_NAMES and
                set(inventory.get('sha256', {})) == base.LEGACY_NAMES, 'Expected the original eleven baseline chapters')
        baseline = {'chapters/' + name: doc for name, doc in inventory['chapters'].items()}
        backup_name = origin_receipt.get('baselineBackup')
        require(isinstance(backup_name, str) and not Path(backup_name).is_absolute() and '..' not in Path(backup_name).parts and
                backup_name.startswith('tools/quest-workbench/backups/'), 'Invalid original baseline backup path')
        self.baseline_backup = self.root / backup_name
        for name, expected_hash in inventory['sha256'].items():
            blob = self.remember(self.baseline_backup / self.roots['client'].relative_to(self.root) / 'chapters' / name)
            require(blob is not None and sha(blob) == expected_hash == origin_receipt['baselineSourceFiles'].get('chapters/' + name) and
                    loads(blob.decode()) == inventory['chapters'][name], f'Frozen tutorial baseline differs from verified backup: {name}')
        require(baseline_contract.get('sourceCurrentDirectory') == CURRENT_SNAPSHOT, 'Unexpected frozen four-chapter snapshot directory')
        snapshot = self.inventory(self.current_snapshot)
        require(set(snapshot) == base.TARGET_NAMES and baseline_contract.get('sourceCurrentChapterHashes') ==
                {name: sha(blob) for name, blob in snapshot.items()}, 'Frozen four-chapter snapshot hashes differ from contract')
        require(all(sha(blob) == origin_receipt['files'].get('chapters/' + name) for name, blob in snapshot.items()),
                'Frozen four-chapter snapshot differs from verified prior installation')
        origin = {'chapters/' + name: loads(blob.decode()) for name, blob in snapshot.items()}
        drafts = self.inventory(self.draft)
        require(set(drafts) == base.TARGET_NAMES, 'Generate exactly the four successor draft chapters')
        draft_blobs = {'chapters/' + name: blob for name, blob in drafts.items()}
        draft_docs = {name: loads(blob.decode()) for name, blob in draft_blobs.items()}
        validation, item_targets = validate_spine(baseline, origin, draft_docs, contract)
        recipe_snapshot = self.recipe_items(item_targets, contract.get('existingItemIds'))
        tag_validation = self.tag_inputs(contract)
        groups = base.replace_group_title(reference['chapter_groups.snbt'], self.remember(self.fragment))
        group_docs = loads(groups.decode())
        for group in (MAIN_GROUP, base.GROUP_ID):
            require(sum(row.get('id') == group for row in group_docs.get('chapter_groups', [])) == 1, f'Missing or duplicate chapter group: {group}')
        manifest_blob = self.remember(self.manifest)
        require(manifest_blob is not None, 'Overlay manifest is required')
        manifest = json.loads(manifest_blob)
        for name in target | {'chapter_groups.snbt'}:
            require(manifest.get(base.PREFIX + name) == sha(reference[name]), f'Overlay manifest mismatch: {name}')
        retired_chapters = {doc['id'].upper() for name, doc in baseline.items() if name not in target}
        retired_objects = set(base.object_ids(origin)) - set(base.object_ids(draft_docs))
        for name in base.LEGACY_NAMES - base.TARGET_NAMES:
            require(base.PREFIX + 'chapters/' + name not in manifest, f'Stale retired chapter manifest entry: {name}')
        manifest.update({base.PREFIX + name: sha(blob) for name, blob in draft_blobs.items()})
        manifest[base.PREFIX + 'chapter_groups.snbt'] = sha(groups)
        self.changes[self.manifest] = base.encoded(manifest)
        counts = {}
        for label, root in self.roots.items():
            for name in base.LEGACY_NAMES:
                path = root / 'chapters' / name
                if path not in self.guards:
                    self.remember(path)
            self.changes.update({root / name: blob for name, blob in draft_blobs.items()})
            self.changes[root / 'chapter_groups.snbt'] = groups
            effective = {**reference, **current[label], **draft_blobs, 'chapter_groups.snbt': groups}
            documents = {name: loads(blob.decode()) for name, blob in effective.items()}
            for name, doc in documents.items():
                if name == MAIN:
                    continue
                if doc.get('group') == MAIN_GROUP:
                    require(type(doc.get('order_index', 0)) in (int, float) and doc.get('order_index', 0) > 1,
                            f'New main chapter must precede existing mainline chapter: {name}')
            for name, doc in documents.items():
                for value in base.strings(doc):
                    for retired in retired_chapters | retired_objects:
                        require(not re.search(r'(?i)(?<![0-9a-f])0*' + format(int(retired, 16), 'x') + r'(?![0-9a-f])', value),
                                f'Reference to retired chapter/object {retired}: {label}/{name}')
            counts[label] = base.validate_graph(documents, label)
            validate_links_and_decorations(documents)
        require(len(set(counts.values())) == 1, 'Effective quest totals differ across roots')
        self.changes = {path: blob for path, blob in self.changes.items() if self.guards[path] != blob}
        self.report = {'kind': KIND, 'createdAt': datetime.now().astimezone().isoformat(), 'mode': 'dry-run', **validation,
                       'totalQuestNodes': counts['client'], 'threeRootSourceHashesMatch': True,
                       'chapterGroupsChanged': groups != reference['chapter_groups.snbt'],
                       'files': {**{name: sha(blob) for name, blob in draft_blobs.items()}, 'chapter_groups.snbt': sha(groups)},
                       'baselineSourceFiles': origin_receipt['baselineSourceFiles'], 'contractSha256': sha(contract_blob),
                       'frozenBaselineSha256': sha(inventory_blob), 'milestoneSnapshotDirectory': CURRENT_SNAPSHOT,
                       'retiredObjectIds': sorted(retired_objects), 'retiredChapterIds': sorted(retired_chapters),
                       'recipeIndexValidation': recipe_snapshot,
                       'tagInputValidation': tag_validation,
                       'changes': {path.relative_to(self.root).as_posix(): {'before': sha(self.guards[path]), 'after': sha(blob)}
                                   for path, blob in self.changes.items()},
                       'checks': ['164 original quest/task IDs, icons, rewards and all 601 description paragraphs preserved',
                                  'only contract-approved checkmarks changed to matching non-consuming item detection',
                                  'all 12 original topic checkmarks retained; only contracted factory milestones retired',
                                  'every new material task and item validated against contract and the actual offline RecipeIndex',
                                  'main chapter ID retained, moved before steam/precision/oil in the existing mainline group',
                                  'unique global IDs, valid dependencies/links/decorations and acyclic dependencies',
                                  'signed-63-bit link targets; three managed mirrors and overlay manifest match',
                                  'scoped backup, concurrent-edit refusal and transaction rollback; unrelated quests untouched'],
                       'existingPlayerProgress': 'Existing task IDs retain saved progress; completed checkmarks are not forcibly revalidated.'}
        return self.report


def main():
    arguments = argparse.ArgumentParser(description=__doc__)
    arguments.add_argument('--apply', action='store_true', help='Install verified drafts with scoped backups and rollback')
    options = arguments.parse_args()
    installation = Installation()
    report = installation.prepare()
    if options.apply:
        report = installation.apply()
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
