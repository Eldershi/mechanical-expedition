"""Build a feature-by-feature Create manual and audit its bounded coverage."""
from collections import Counter, defaultdict
from datetime import datetime
from html import escape
import hashlib
import json
from pathlib import Path
import re
import shutil
import zipfile
from zoneinfo import ZoneInfo

from ftb_snbt import loads
from mainline_guide_utils import replace_description

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[1]
EVIDENCE = ROOT / 'evidence/create-basics-20261018'
QUESTS = ROOT / 'instance/config/ftbquests/quests'
JAR = ROOT / 'instance/mods/create-1.20.1-6.0.8.jar'
FILES = ['motion-control.json', 'process-fluids.json', 'logistics-trains.json', 'structures-information.json']
ORDER = ['orientation', 'motion', 'create_processing', 'create_logistics', 'create_fluids', 'structures',
         'redstone', 'create_packages', 'create_trains', 'information', 'create_equipment']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sid(key):
    return f'{int(hashlib.sha256(("expedition:create-basics:" + key).encode()).hexdigest()[:16], 16) & ((1 << 63) - 1):016X}'


GROUP = sid('group')


def q(value):
    return json.dumps(value, ensure_ascii=False)


def read_entries():
    chapters = {}
    for filename in FILES:
        doc = json.loads((EVIDENCE / filename).read_text())
        for chapter in doc['chapters']:
            assert chapter['key'] not in chapters, chapter['key']
            for entry in chapter['entries']:
                entry['blocks'] = [b.removeprefix('create:') for b in entry.get('blocks', [])]
                entry['featureKey'] = entry.get('key', entry['item'].split(':')[-1])
                entry['questId'] = sid(chapter['key'] + ':' + entry['featureKey'])
            chapters[chapter['key']] = chapter
    return [chapters[key] for key in ORDER]


def block_inventory(chapters):
    with zipfile.ZipFile(JAR) as z:
        blocks = {n.removeprefix('assets/create/blockstates/').removesuffix('.json') for n in z.namelist()
                  if n.startswith('assets/create/blockstates/') and n.endswith('.json')}
        item_models = {n.removeprefix('assets/create/models/item/').removesuffix('.json') for n in z.namelist()
                       if n.startswith('assets/create/models/item/') and n.endswith('.json')}
    owners = defaultdict(list)
    entries = [e for c in chapters for e in c['entries']]
    by_feature = {e['featureKey']: e for e in entries}
    assert len(by_feature) == len(entries), 'Feature keys must remain unique, including special internal-state guides'
    for entry in entries:
        for block in entry['blocks']:
            assert block in blocks, (entry['title'], block)
            owners[block].append(entry['questId'])
        ns, name = entry['item'].split(':', 1)
        assert ns == 'minecraft' or (ns == 'create' and name in item_models), entry['item']
    # Colour/material appearances and engine-managed states share a behaviour.
    suffix_owner = {'seat': 'white_seat', 'table_cloth': 'white_table_cloth', 'postbox': 'white_postbox',
                    'valve_handle': 'copper_valve_handle', 'nixie_tube': 'nixie_tube',
                    'toolbox': 'brown_toolbox', 'sail': 'white_sail'}
    internal_owner = {'crushing_wheel_controller': 'crushing_wheel', 'lit_blaze_burner': 'blaze_burner',
                      'fake_track': 'track', 'minecart_anchor': 'cart_assembler', 'powered_shaft': 'steam_engine'}
    material = {'asurine', 'crimsite', 'ochrum', 'veridium', 'scoria', 'scorchia', 'limestone',
                'rose_quartz_block', 'raw_zinc_block', 'zinc_block', 'zinc_ore', 'deepslate_zinc_ore',
                'andesite_alloy_block', 'brass_block', 'industrial_iron_block', 'weathered_iron_block',
                'experience_block', 'refined_radiance_casing', 'shadow_steel_casing',
                'cardboard_block', 'bound_cardboard_block', 'honey', 'chocolate'}
    decorations = {'wooden_bracket', 'metal_bracket', 'framed_glass', 'framed_glass_pane', 'horizontal_framed_glass',
                   'horizontal_framed_glass_pane', 'vertical_framed_glass', 'vertical_framed_glass_pane',
                   'tiled_glass', 'tiled_glass_pane'}
    records, unknown = [], []
    for block in sorted(blocks):
        if block in owners:
            records.append({'block': block, 'role': 'taught', 'questIds': sorted(set(owners[block]))})
            continue
        if block == 'metal_girder':
            records.append({'block': block, 'role': 'decorative_referenced',
                            'reason': 'structural decoration and shaft-encasing explanation accompanies the shaft tutorial',
                            'questIds': [by_feature['shaft']['questId']]})
            continue
        owner = internal_owner.get(block)
        reason = 'internal state covered with its parent machine'
        if not owner:
            for suffix, family in suffix_owner.items():
                if block.endswith('_' + suffix):
                    owner, reason = family, 'same-function colour or appearance variant'
                    break
        if owner:
            assert owner in by_feature, (block, owner)
            records.append({'block': block, 'role': 'taught_variant', 'reason': reason,
                            'questIds': [by_feature[owner]['questId']]})
        elif block in material:
            records.append({'block': block, 'role': 'material_or_natural_block', 'reason': 'ingredient, resource or fluid, not a separate machine'})
        elif block in decorations or any(s in block for s in ['window', '_pillar', '_bars',
                'cut_', 'layered_', '_tiles', '_tile_slab', '_tile_stairs', '_shingles', '_shingle_slab',
                '_shingle_stairs', 'metal_girder']) or (block.startswith('small_') and '_brick' in block):
            records.append({'block': block, 'role': 'decorative_palette', 'reason': 'building palette, no separate automation behaviour'})
        else:
            unknown.append(block)
            records.append({'block': block, 'role': 'unclassified'})
    assert not unknown, 'Review these unclassified blockstates before claiming bounded coverage: ' + ', '.join(unknown)
    return records, item_models


def chapter_snbt(chapter, order):
    rows = ['{', f'\tid: {q(sid("chapter:" + chapter["key"]))}',
            f'\tfilename: {q("create_basics_" + chapter["key"])}', f'\tgroup: {q(GROUP)}',
            f'\ttitle: {q(chapter["title"])}', f'\ticon: {q(chapter["entries"][0]["item"])}',
            f'\torder_index: {order}', '\tdefault_hide_dependency_lines: false', '\tquests: [']
    for index, entry in enumerate(chapter['entries']):
        rows += ['\t\t{', f'\t\t\tid: {q(entry["questId"])}', f'\t\t\ttitle: {q(entry["title"])}',
                 f'\t\t\ticon: {q(entry.get("icon", entry["item"]))}', f'\t\t\tx: {index % 4 * 5}.0d',
                 f'\t\t\ty: {index // 4 * 3}.0d', '\t\t\tdescription: [']
        rows += ['\t\t\t\t' + q(s) for s in entry['description']]
        rows += ['\t\t\t]', '\t\t\ttasks: [{', f'\t\t\t\tid: {q(sid("task:" + entry["questId"]))}',
                 '\t\t\t\ttype: "checkmark"', '\t\t\t\ttitle: "已了解用途与操作"', '\t\t\t}]', '\t\t}']
    rows += ['\t]', '}', '']
    result = '\n'.join(rows)
    loads(result)
    return result


def main():
    chapters = read_entries()
    inventory, models = block_inventory(chapters)
    before = json.loads((EVIDENCE / 'before-files.json').read_text())
    old_dir = Path(before['backup']) / 'instance/config/ftbquests/quests'
    old_chapters = [loads(p.read_text()) for p in (old_dir / 'chapters').glob('*.snbt')]
    old_quests = [entry for c in old_chapters for entry in c.get('quests', [])]
    coverage = []
    for chapter in chapters:
        for entry in chapter['entries']:
            previous = [quest for quest in old_quests if any(t.get('item') == entry['item'] for t in quest.get('tasks', []))]
            single = [quest for quest in previous if len(quest.get('tasks', [])) == 1 and quest.get('description')]
            assert len(entry['description']) >= 3 and sum(map(len, entry['description'])) >= 80, entry['title']
            assert entry.get('sources'), entry['title']
            coverage.append({'feature': entry['featureKey'], 'title': entry['title'], 'item': entry['item'],
                'chapter': chapter['key'], 'questId': entry['questId'], 'blocks': entry['blocks'],
                'beforeAnyItemTaskReference': bool(previous), 'beforeSingleItemTaskWithBody': bool(single),
                'afterDedicatedInstruction': True, 'sources': entry['sources']})
    files = {}
    for order, chapter in enumerate(chapters):
        files['chapters/create_basics_' + chapter['key'] + '.snbt'] = chapter_snbt(chapter, order)
    path = QUESTS / 'chapter_groups.snbt'
    text = path.read_text()
    groups = loads(text)['chapter_groups']
    if not any(g['id'] == GROUP for g in groups):
        point = text.rfind(']')
        text = text[:point] + f'\t\t{{ id: {q(GROUP)}, title: "机械动力·逐功能教程" }}\n\t' + text[point:]
    loads(text)
    files['chapter_groups.snbt'] = text
    # Point the existing welcome text at the new manual while retaining its IDs.
    path = QUESTS / 'chapters/prologue.snbt'
    text = path.read_text()
    data = loads(text)
    quest = next(q for q in data['quests'] if q['id'] == '1EA33F05E5B01612')
    note = '基础机器不会用时，可查阅“机械动力起步”“物流与仓储”“农业与生产”“铁路与运输”，了解安装、操作与排错。'
    if note not in quest['description']:
        text = replace_description(text, quest['id'], quest['description'] + ['{@pagebreak}', note])
    files['chapters/prologue.snbt'] = text
    for name, text in files.items():
        (QUESTS / name).write_text(text)
    counts = Counter(row['role'] for row in inventory)
    report = {'builtAt': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        'scope': 'Installed Create 6.0.8 functional block families plus common functional items; not all addon registries.',
        'tutorialChapters': len(chapters), 'tutorialEntries': len(coverage), 'blockstateResourcesReviewed': len(inventory),
        'classificationCounts': dict(counts), 'unclassifiedBlockstates': [],
        'functionalAndVariantStatesCovered': sum(n for role, n in counts.items() if role.startswith('taught')),
        'beforeFeaturesWithAnyItemTask': sum(c['beforeAnyItemTaskReference'] for c in coverage),
        'beforeFeaturesWithSingleItemTaskAndBody': sum(c['beforeSingleItemTaskWithBody'] for c in coverage),
        'afterFeaturesWithDedicatedInstruction': len(coverage), 'coverage': coverage, 'blockInventory': inventory,
        'sourceFiles': {f: sha(EVIDENCE / f) for f in FILES}, 'createJarSha256': sha(JAR),
        'contentHash': {name: hashlib.sha256(text.encode()).hexdigest() for name, text in files.items()},
        'rules': ['One independent node per function, with colour and internal-state aliases explicitly mapped.',
                  'No template that substitutes only the item name for real instructions.',
                  'All new reading tasks are checkmarks without rewards or progression gates.',
                  'Pure palette/material resources are individually classified, not counted as machine tutorials.'],
        'gameOrServerStarted': False, 'runtimeValidated': False}
    (EVIDENCE / 'coverage-audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['tutorialChapters', 'tutorialEntries', 'blockstateResourcesReviewed',
        'functionalAndVariantStatesCovered', 'classificationCounts', 'beforeFeaturesWithSingleItemTaskAndBody']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
