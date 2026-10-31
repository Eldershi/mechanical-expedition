"""Apply narrow compatibility data corrections; retain original mod downloads."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
INSTANCE = ROOT / 'instance'
generated = []


def jar(pattern):
    return next(p for p in (INSTANCE / 'mods').glob('*.jar') if p.match(pattern))


def read(pattern, name):
    with zipfile.ZipFile(jar(pattern)) as z:
        return json.loads(z.read(name))


def write(name, data):
    p = INSTANCE / 'kubejs' / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    generated.append(name)


# Empty obsolete Patchouli extension declaration contains no pages. In 1.20,
# extensions ship resources in the parent book's namespace rather than declaring extend.
p = jar('ars_controle*.jar')
original = ROOT / 'backups/before-runtime-fixes-20261016/mods' / p.name
assert original.exists()
temporary = p.with_suffix('.patched')
with zipfile.ZipFile(original) as src, zipfile.ZipFile(temporary, 'w') as dst:
    for info in src.infolist():
        if info.filename == 'data/ars_controle/patchouli_books/ars_controle/book.json':
            continue
        dst.writestr(info, src.read(info.filename))
temporary.replace(p)

name = 'data/the_bumblezone/bz_pollen_puff_entity_flowers/goety.json'
data = read('the_bumblezone*.jar', name)
write(name, {key.replace('_servent', '_servant'): value for key, value in data.items()})

# This 1.20.1 backport accidentally shipped 1.21 written-book loot functions.
def correct_loot(data):
    if isinstance(data, list):
        return [correct_loot(x) for x in data]
    if not isinstance(data, dict):
        return data
    if data.get('function') == 'minecraft:set_written_book_pages':
        pages = ','.join(json.dumps(json.dumps(page, ensure_ascii=False), ensure_ascii=False) for page in data['pages'])
        fixed = {'function': 'minecraft:set_nbt',
                 'tag': '{title:"Citadel Records",author:"Unknown",resolved:1b,pages:[' + pages + ']}' }
        if 'conditions' in data:
            fixed['conditions'] = data['conditions']
        return fixed
    fixed = {key: correct_loot(value) for key, value in data.items()}
    if fixed.get('type') == 'minecraft:loot_table' and 'value' in fixed and 'name' not in fixed:
        fixed['name'] = fixed.pop('value')
    return fixed


for relative in ['chests/citadel/citadel_tomes', 'chests/catacombs/crypt_loot']:
    name = 'data/irons_spellbooks/loot_tables/' + relative + '.json'
    write(name, correct_loot(read('irons_spellbooks*.jar', name)))

# Old Nether's Delight is absent in the CMI base. Preserve the table and weights,
# using empty outcomes for that optional mod's entries rather than invalid items.
name = 'data/goety_revelation/loot_tables/inject/chests/goety_revelation/church_food_2.json'
data = read('GoetyRevelation*.jar', name)
for pool in data['pools']:
    pool['entries'] = [({'type':'minecraft:empty', 'weight':entry.get('weight', 1)}
                        if entry.get('name', '').startswith('nethersdelight:') else entry)
                       for entry in pool['entries']]
write(name, data)

name = 'data/legendary_monsters/advancements/defeat_ambusher.json'
data = read('legendarymonsters*.jar', name)
data['display']['icon']['item'] = 'legendary_monsters:chiseled_ancient_dripstone_shard'
write(name, data)

name = 'data/terramity/advancements/fairy_advancement.json'
data = read('terramity*.jar', name)
data['parent'] = 'terramity:terramity_parent_advancement'
write(name, data)

# Fix actual food ID in the mutant turret repair tag.
name = 'data/mutantmore/tags/items/repairs_mutant_shulker_turret.json'
data = read('mutantmore*.jar', name)
data['values'] = ['minecraft:cod' if v == 'minecraft:raw_cod' else v for v in data['values']]
write(name, data)

# Normalize multi-loader ingredient placeholders to the Forge value.
for wood in ['aurum', 'edelwood']:
    name = 'data/forbidden_arcanus/recipes/' + wood + '_chest_boat.json'
    data = read('forbidden_arcanus*.jar', name)
    data['ingredients'] = [x.get('forge_value', x) for x in data['ingredients']]
    write(name, data)

# Respect explicit CC exclusion; these optional recipes must not force it back in.
for kind in ['recipes/crafting/trains/network_monitor', 'advancements/recipes/misc/crafting/trains/network_monitor']:
    name = 'data/createadditionallogistics/' + kind + '.json'
    data = read('createadditionallogistics*.jar', name)
    if kind.startswith('recipes/'):
        data['conditions'] = [{'type':'forge:mod_loaded', 'modid':'computercraft'}]
    else:
        # The recipe is unavailable without CC; its unlock advancement has no display.
        data = {'parent':'minecraft:recipes/root', 'criteria':{'optional_cc':{'trigger':'minecraft:impossible'}}}
    write(name, data)

report = {'generatedDataOverrides':generated,
          'jarPatch':{'file':p.name, 'original':str(original),
                      'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                      'change':'Remove obsolete empty Patchouli extension declaration; no bytecode or guide pages removed.'}}
(ROOT / 'evidence/mod-install/compatibility-data.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({'dataOverrides':len(generated),'jarPatch':p.name}))
