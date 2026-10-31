#!/usr/bin/env python3
"""Build additive HNN 5.3.3 models for the installed Iron's Spellbooks 3.16.3."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parent
ACTIVE = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
PAYLOAD = ROOT / 'payload'
IRON = 'irons_spellbooks:'


def drop(item, count=1):
    return {'item': item if ':' in item else IRON + item, 'count': count}


INK = [drop('common_ink', 4), drop('uncommon_ink', 2), drop('rare_ink'), drop('epic_ink')]
ESSENCE = drop('arcane_essence', 16)
SPECS = [
    ('necromancer', 256, '#7B5AA6', 0.8, [ESSENCE]),
    ('pyromancer', 256, '#F28C28', 0.8, [ESSENCE] + INK),
    ('cryomancer', 256, '#72D8F0', 0.8, [ESSENCE] + INK),
    ('archevoker', 512, '#B37BE3', 0.8, [ESSENCE] + INK + [drop('evocation_rune'), drop('evoker_spell_book')]),
    ('apothecarist', 256, '#8BC34A', 0.8, [ESSENCE] + INK),
    ('priest', 256, '#F2E6A2', 0.8, [ESSENCE] + INK),
    ('cultist', 256, '#C94464', 0.8, [ESSENCE] + INK),
    ('citadel_keeper', 1024, '#CF754C', 0.6, [drop('cinder_essence', 4), drop('minecraft:netherite_scrap', 4)]),
    ('ice_spider', 256, '#9BDDED', 0.8, [ESSENCE, drop('minecraft:string', 16), drop('icy_fang', 2)]),
    ('dead_king', 4096, '#BA8BE3', 0.5, [drop('arcane_essence', 32), drop('blank_rune', 4), drop('rare_ink'), drop('epic_ink'), drop('legendary_ink'), drop('blood_staff'), drop('necronomicon_spell_book'), drop('bone_key')]),
    ('fire_boss', 8192, '#FF7138', 0.4, [drop('arcane_essence', 32), drop('cinder_essence', 8), drop('divine_soulshard'), drop('decrepit_scythe'), drop('betrayer_signet'), drop('decrepit_key')]),
]


def write_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')


def main():
    jar = ACTIVE / 'mods/irons_spellbooks-1.20.1-3.16.3.jar'
    with zipfile.ZipFile(jar) as z:
        names = json.loads(z.read('assets/irons_spellbooks/lang/zh_cn.json'))
        for entity, *_ in SPECS:
            assert f'data/irons_spellbooks/loot_tables/entities/{entity}.json' in z.namelist(), entity
    specs = []
    for entity, cost, color, scale, drops in SPECS:
        boss = entity in {'dead_king', 'fire_boss'}
        nether = entity in {'pyromancer', 'citadel_keeper', 'fire_boss'}
        model = {
            'conditions': [{'type': 'forge:mod_loaded', 'modid': 'irons_spellbooks'}],
            'entity': IRON + entity,
            'variants': [],
            'name': 'entity.irons_spellbooks.' + entity,
            'name_color': color,
            'gui_scale': scale,
            'gui_x_offset': 0,
            'gui_y_offset': 0,
            'gui_z_offset': 0,
            'sim_cost': cost,
            'input': drop('hostilenetworks:prediction_matrix'),
            'base_drop': drop('hostilenetworks:nether_prediction' if nether else 'hostilenetworks:overworld_prediction'),
            'fabricator_drops': drops,
            'tier_data': [6, 54, 354, 1254],
            'data_per_kill': [3, 12, 30, 45] if boss else [1, 4, 10, 18],
        }
        assert len({d['item'] for d in drops}) == len(drops)
        assert all(1 <= d['count'] <= 64 for d in drops)
        assert not any(d['item'] == IRON + 'scroll' for d in drops)
        write_json(PAYLOAD / f'kubejs/data/expedition/data_models/irons_spellbooks/{entity}.json', model)
        specs.append({'id': 'expedition:irons_spellbooks/' + entity, 'displayName': names[model['name']], **model})
    write_json(PAYLOAD / 'kubejs/config/expedition-irons-hnn-models.json', {
        'schemaVersion': 1,
        'sourceVersion': 'irons_spellbooks-1.20.1-3.16.3',
        'models': specs,
        'notes': [
            'Additive independent models; existing models and recipes are not changed.',
            'Random spell scrolls are omitted because their loot function creates required spell NBT.',
            'Boss keys come from native per-player loot tables.',
            'Summons, projectiles, corpse/soul, debug entities and dynamic equipment-only entities are excluded.',
            'Catacombs zombie and magehunter vindicator use vanilla runtime entity types and retain vanilla HNN coverage.'
        ],
    })
    print(json.dumps({'modelCount': len(specs), 'dropOptions': sum(len(s['fabricator_drops']) for s in specs),
                      'sourceSha256': hashlib.sha256(jar.read_bytes()).hexdigest()}, indent=2))


if __name__ == '__main__':
    main()
