"""Build data overrides for retired adventure content; never edit JARs or worlds."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INSTANCE = ROOT / 'instance'
BACKUP = ROOT / 'backups/before-mod-removal-20261018'
REPORT = ROOT.parents[1] / 'design/current-mod-checklist/removal-20261018'
REMOVED = {'goety', 'goety_revelation', 'iceandfire', 'livingthings', 'mowziesmobs'}
ORIGINS_PATH = BACKUP / 'adventure-override-origins.json'
ORIGINS = json.loads(ORIGINS_PATH.read_text()) if ORIGINS_PATH.exists() else {}


def retired(value):
    return isinstance(value, str) and value.partition(':')[0] in REMOVED


def digest(value):
    return hashlib.sha256(value).hexdigest()


def source(jar_pattern, member):
    jars = sorted((INSTANCE / 'mods').glob(jar_pattern))
    if len(jars) != 1:
        raise RuntimeError(f'Expected one retained JAR for {jar_pattern}: {jars}')
    jar = jars[0]
    with zipfile.ZipFile(jar) as archive:
        raw = archive.read(member)
    archived = BACKUP / 'jar-resources' / jar.name / member
    if not archived.exists():
        archived.parent.mkdir(parents=True, exist_ok=True)
        archived.write_bytes(raw)
    return json.loads(raw), {'jar': str(jar), 'member': member,
                             'sourceSha256': digest(raw), 'originalResource': str(archived)}


def write_override(member, data, evidence, removed_entries):
    # KubeJS exposes kubejs/data/<namespace>/... as data/<namespace>/... .
    destination = INSTANCE / 'kubejs' / member
    key = str(destination.relative_to(ROOT))
    archived = BACKUP / destination.relative_to(ROOT)
    if key not in ORIGINS:
        existed = destination.exists()
        if existed and not archived.exists():
            archived.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(destination, archived)
        ORIGINS[key] = {'existedBefore': existed,
                        'sha256Before': digest(destination.read_bytes()) if existed else None}
        ORIGINS_PATH.parent.mkdir(parents=True, exist_ok=True)
        ORIGINS_PATH.write_text(json.dumps(ORIGINS, ensure_ascii=False, indent=2) + '\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
    destination.write_bytes(raw)
    return {**evidence, 'destination': str(destination), **ORIGINS[key],
            'sha256': digest(raw), 'removedEntries': removed_entries}


def item_entries(value):
    if isinstance(value, list):
        return sum((item_entries(x) for x in value), [])
    if isinstance(value, dict):
        own = [json.dumps(value, sort_keys=True)] if value.get('type') in {'item', 'minecraft:item'} else []
        return own + sum((item_entries(x) for x in value.values()), [])
    return []


def strip_loot(value, removed_entries):
    if isinstance(value, list):
        cleaned = []
        for entry in value:
            if isinstance(entry, dict) and entry.get('type') in {'item', 'minecraft:item'} and retired(entry.get('name')):
                removed_entries.append(entry)
            else:
                cleaned.append(strip_loot(entry, removed_entries))
        return cleaned
    if isinstance(value, dict):
        return {key: strip_loot(entry, removed_entries) for key, entry in value.items()}
    return value


def main():
    changes = []
    for biome in ['crimson_forest', 'soul_sand_valley']:
        member = f'data/allthemodium/worldgen/biome/{biome}.json'
        original, evidence = source('allthemodium-*.jar', member)
        data = json.loads(json.dumps(original))
        removed_entries = []
        for category, entries in data['spawners'].items():
            removed_entries.extend({'category': category, **entry} for entry in entries if retired(entry['type']))
            data['spawners'][category] = [entry for entry in entries if not retired(entry['type'])]
        assert {key: value for key, value in data.items() if key != 'spawners'} == {
            key: value for key, value in original.items() if key != 'spawners'}
        for category, entries in original['spawners'].items():
            assert data['spawners'][category] == [entry for entry in entries if not retired(entry['type'])]
        assert removed_entries, f'No retired spawns found in {member}'
        changes.append(write_override(member, data, evidence, removed_entries))

    member = 'data/idas/integrated_structure_spawners/dread_citadel.json'
    original, evidence = source('idas_forge-*.jar', member)
    removed_entries = [entry for entry in original['mobs'] if retired(entry['name'])]
    data = {**original, 'mobs': [entry for entry in original['mobs'] if not retired(entry['name'])]}
    # Integrated API accepts an empty list: zero total weight returns null, and
    # SpawnerRandomizingProcessor substitutes its configured replacement block.
    changes.append(write_override(member, data, evidence, removed_entries))

    loot_paths = [
        'dread_citadel/dread_citadel', 'dread_citadel/dread_citadel_library',
        'dread_citadel/dread_citadel_throne', 'haunted_manor/if_haunted_manor',
        'labyrinth/if_labyrinth_tomb',
    ]
    for loot in loot_paths:
        member = f'data/idas/loot_tables/chests/{loot}.json'
        original, evidence = source('idas_forge-*.jar', member)
        removed_entries = []
        data = strip_loot(original, removed_entries)
        # Empty pools have no drops; removing them avoids parser assumptions.
        data['pools'] = [pool for pool in data.get('pools', []) if pool.get('entries')]
        assert Counter(item_entries(data)) == Counter(
            entry for entry in item_entries(original)
            if not retired(json.loads(entry).get('name')))
        assert not any(f'"{namespace}:' in json.dumps(data) for namespace in REMOVED)
        changes.append(write_override(member, data, evidence, removed_entries))

    # These are untouched optional structure gates, recorded for reproducibility.
    conditional_structures = []
    for name in ['iceandfire/dread_citadel', 'iceandfire/sirens_cove', 'haunted_manor', 'labyrinth']:
        data, evidence = source('idas_forge-*.jar', f'data/idas/worldgen/structure/{name}.json')
        conditional_structures.append({**evidence, 'type': data['type'],
                                       'required_mods': data.get('required_mods'),
                                       'change_pool_mods': data.get('change_pool_mods')})
    REPORT.mkdir(parents=True, exist_ok=True)
    result = {'generator': str(Path(__file__).resolve()), 'changes': changes,
              'idasExistingOptionalStructureGates': conditional_structures,
              'validation': {'biomeNonSpawnerFieldsUnchanged': True,
                             'remainingBiomeSpawnsUnchanged': True,
                             'remainingLootItemEntriesUnchanged': True,
                             'retiredNamespaceReferencesInOverrides': 0,
                             'runtimeValidation': 'Root task will test; no Minecraft launched here.'}}
    (REPORT / 'adventure-data-overrides.json').write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'overrides': len(changes),
                      'removedBiomeSpawns': sum(len(x['removedEntries']) for x in changes[:2]),
                      'removedIdasSpawnerEntries': len(changes[2]['removedEntries']),
                      'removedLootEntries': sum(len(x['removedEntries']) for x in changes[3:])}))


if __name__ == '__main__':
    main()
