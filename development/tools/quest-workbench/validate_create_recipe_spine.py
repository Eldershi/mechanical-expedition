#!/usr/bin/env python3
"""Read-only check of quest edges against the actual completed JEI export."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from recipe_data import RecipeIndex

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DRAFT = ROOT / 'design/create-recipe-spine-draft'
spec = importlib.util.spec_from_file_location('recipe_spine_snbt', ROOT / 'clients/cmi-expedition/tools/ftb_snbt.py')
snbt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(snbt)


def require(value, message):
    if not value:
        raise ValueError(message)


def validate():
    contract = json.loads((DRAFT / 'contract.json').read_text())
    documents = {p.name: snbt.loads(p.read_text()) for p in (DRAFT / 'chapters').glob('*.snbt')}
    quests = {q['id']: q for d in documents.values() for q in d['quests']}
    records = {row['questId']: row for row in contract['originalTaskConversions'] + contract['newMaterialQuests']}
    index = RecipeIndex(HERE)
    index._load()
    require(index.active_export is not None, 'No completed JEI export')

    def item_for_key(key):
        return index._by_key.get(key, {}).get('id', key.split('|', 1)[-1])

    def values(slots):
        return [{item_for_key(option[0]) for option in slot} for slot in slots]

    recipe_cache = {}

    def recipes(item, recipe_id):
        key = (item, recipe_id)
        if key not in recipe_cache:
            target = index._by_id.get(item)
            require(target, f'Unknown JEI output {item}')
            matches = []
            for ci, ri in index._index.get(target['k'], {}).get('p', []):
                recipe = index._category_recipes(ci)[ri]
                if recipe.get('id') != recipe_id:
                    continue
                if item not in set().union(set(), *values(recipe.get('out', []))):
                    continue
                category = index._categories[ci]
                machines = {item_for_key(k) for k in category.get('catalysts', [])}
                matches.append((recipe, category['id'], machines))
            require(matches, f'No actual output recipe: {item} / {recipe_id}')
            recipe_cache[key] = matches
        return recipe_cache[key]

    for row in records.values():
        if row.get('selectedRecipeId') and isinstance(row['item'], str):
            recipes(row['item'], row['selectedRecipeId'])

    evidence_edges = set()
    machine_edges = 0
    for edge in contract['dependencyEvidence']:
        parent, child = edge['fromQuestId'], edge['toQuestId']
        require(parent in records and child in records, f'Unknown core edge {parent} -> {child}')
        require(parent in quests[child].get('dependencies', []), f'Evidence is not a saved dependency: {parent} -> {child}')
        output = records[child]['item']
        require(isinstance(output, str), f'Unexpected filter as a processing output: {child}')
        source = records[parent]
        require(edge['recipeId'] == records[child]['selectedRecipeId'],
                f'Prerequisites from incompatible recipe routes were mixed: {child}')
        accepted = set(source.get('matchedItemIds', [])) or {source['item']}
        actual = recipes(output, edge['recipeId'])
        if edge['relation'] == 'ingredient':
            slot_indexes = edge.get('slotIndexes', [])
            require(slot_indexes, f'Ingredient edge has no input slot: {edge}')
            require(any(all(i < len(r.get('in', [])) and accepted & values(r['in'])[i]
                            for i in slot_indexes) for r, _, _ in actual), f'No real ingredient edge: {edge}')
        elif edge['relation'] == 'machine':
            machine_edges += 1
            require(any(accepted & machines for _, _, machines in actual), f'No actual JEI processing machine: {edge}')
        else:
            raise ValueError(f'Unknown core relation: {edge["relation"]}')
        evidence_edges.add((parent, child))

    core_edges = {(parent, child) for child in records for parent in quests[child].get('dependencies', [])}
    require(core_edges == evidence_edges, 'Some core prerequisites lack actual recipe/machine evidence')
    main = documents['create_basics_orientation.snbt']
    hidden_edges = set()
    machine_pairs = {(e['fromQuestId'], e['toQuestId']) for e in contract['dependencyEvidence'] if e['relation'] == 'machine'}
    for rule in main.get('quest_enhance_hidden_dependency_lines', []):
        child = f'{int(rule["source"].removeprefix("q:"), 16):016X}'
        parent = f'{int(rule["dependency"].removeprefix("q:"), 16):016X}'
        pair = (parent, child)
        require(rule['source'] == f'q:{int(child, 16):x}' and rule['dependency'] == f'q:{int(parent, 16):x}',
                'Hidden line keys do not match native Quest Enhance encoding')
        require(rule.get('reveal_on_hover') is False and pair in core_edges and pair not in machine_pairs,
                'A processing capability or non-existent prerequisite was hidden')
        remaining = core_edges - {pair}
        visited, pending = set(), [parent]
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(b for a, b in remaining if a == node)
        require(child in visited, 'A hidden prerequisite lacks a visible indirect recipe path')
        hidden_edges.add(pair)
    # All hidden edges must also have an indirect route after hiding the full set.
    for parent, child in hidden_edges:
        visited, pending = set(), [parent]
        while pending:
            node = pending.pop()
            if node in visited:
                continue
            visited.add(node)
            pending.extend(b for a, b in core_edges - hidden_edges if a == node)
        require(child in visited, 'Combined hidden lines disconnect a recipe prerequisite')
    require(main['group'] == '050255AE19A93344' and main['order_index'] < 2,
            'Create bootstrap must precede the existing three main chapters')
    require(not any(q['id'] in contract['oldMilestonesRemoved'] for q in quests.values()),
            'An abstract factory milestone remains')
    for row in records.values():
        task = quests[row['questId']]['tasks'][0]
        require(task['type'] == 'item' and task.get('consume_items') is False and
                task.get('only_from_crafting') is False, f'Invalid non-consuming item detection: {row["questId"]}')

    item_to_id = {r['item']: r['questId'] for r in records.values() if isinstance(r['item'], str)}
    for metal in ['iron', 'gold', 'copper']:
        plate = item_to_id[f'thermal:{metal}_plate']
        require((item_to_id['create:mechanical_press'], plate) in evidence_edges,
                f'Press capability missing for {metal} plates')
    for item in ['create:goggles', 'create:wrench']:
        require((item_to_id['thermal:gold_plate'], item_to_id[item]) in evidence_edges,
                f'Gold plate input missing for {item}')
    require((item_to_id['minecraft:iron_ingot'], item_to_id['minecraft:gold_ingot']) not in evidence_edges and
            (item_to_id['minecraft:gold_ingot'], item_to_id['minecraft:iron_ingot']) not in evidence_edges,
            'Parallel raw metals were artificially ordered')
    return {'coreItems': len(records), 'actualRecipeEdges': len(evidence_edges),
            'processingMachineEdges': machine_edges, 'jeiRecipeVariantsChecked': sum(map(len, recipe_cache.values())),
            'hiddenRedundantRecipeEdges': len(hidden_edges), 'visibleRecipeEdges': len(core_edges - hidden_edges),
            'mainGroup': main['group'], 'mainOrder': main['order_index'],
            'validatedAgainst': str(index.active_export.relative_to(ROOT)), 'status': 'passed'}


if __name__ == '__main__':
    print(json.dumps(validate(), ensure_ascii=False, indent=2))
