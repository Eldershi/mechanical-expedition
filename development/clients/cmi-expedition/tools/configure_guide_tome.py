"""Build the guide catalogue and restore the Tome's Chinese item name."""

import argparse
import json
from pathlib import Path
import re
import tomllib
import zipfile

PROJECT = Path(__file__).resolve().parents[3]
REMOVED_CONTENT_MODS = {'goety', 'goety_revelation', 'iceandfire', 'livingthings', 'mowziesmobs'}
DIRECT = [
    'ftbquests:book', 'ae2:guide', 'immersiveengineering:manual',
    'tconstruct:materials_and_you', 'tconstruct:puny_smelting',
    'tconstruct:mighty_smelting', 'tconstruct:tinkers_gadgetry',
    'tconstruct:fantastic_foundry', 'tconstruct:encyclopedia',
    'alexscaves:cave_book', 'edenring:guide_book', 'aether:book_of_lore',
    'botania:lexicon', 'ars_nouveau:worn_notebook', 'eidolon:codex',
    'enigmaticlegacy:the_acknowledgment', 'malum:encyclopedia_arcana',
    'eternal_starlight:book', 'solcarrot:food_book',
]


def catalog(instance):
    books = [{'id': item} for item in DIRECT]
    native_guides = {}
    for jar in sorted((instance / 'mods').glob('*.jar')):
        with zipfile.ZipFile(jar) as archive:
            for name in sorted(archive.namelist()):
                if name in {'data/scguns/guides/supply_scamp.json', 'data/scguns/guides/viventrum.json'}:
                    definition = json.loads(archive.read(name))
                    native_guides[definition['id']] = definition
                    continue
                parts = name.split('/')
                if (len(parts) != 5 or parts[0] not in {'data', 'assets'}
                        or parts[2] != 'patchouli_books' or parts[4] != 'book.json'
                        or parts[1] in REMOVED_CONTENT_MODS):
                    continue
                book = json.loads(archive.read(name))
                if book.get('extend'):
                    continue
                if book.get('custom_book_item'):
                    books.append({'id': book['custom_book_item']})
                elif not book.get('dont_generate_book'):
                    books.append({'id': 'patchouli:guide_book',
                                  'nbt': {'patchouli:book': parts[1] + ':' + parts[3]}})
    # Scorched Guns generates these tutorial books through its native helper.
    for entity in ['scguns:supply_scamp', 'scguns:viventrum']:
        books.append({'id': 'minecraft:written_book', 'factory': 'scguns:mob_guide',
                      'entity': entity, 'definition': native_guides[entity]})
    for hint, pages in [('darktower', 3), ('hydralair', 4), ('icetower', 3),
                        ('labyrinth', 5), ('lichtower', 4), ('tfstronghold', 4),
                        ('trollcave', 3), ('yeticave', 3)]:
        books.append({'id': 'minecraft:written_book', 'factory': 'twilightforest:structure_hint',
                      'hint': hint, 'pages': pages})
    for variant in ['PILLAGER_SHIP', 'PILLAGER_OUTPOST', 'PILLAGER_SHELTER']:
        books.append({'id': 'minecraft:written_book', 'factory': 'aquamirae:logbook', 'variant': variant})
    # Thermal registers its Patchouli book in code.
    books.append({'id': 'patchouli:guide_book', 'nbt': {'patchouli:book': 'thermal:guidebook'}})
    unique = {}
    for book in books:
        unique.setdefault(json.dumps(book, sort_keys=True), book)
    return list(unique.values())


def restore_name(source, target):
    """Preserve archive entries and metadata, changing only the mistranslated name."""
    with zipfile.ZipFile(source) as archive:
        entries = [(info, archive.read(info)) for info in archive.infolist()]
        comment = archive.comment
    changed = False
    for index, (info, raw) in enumerate(entries):
        if info.filename == 'assets/eccentrictome/lang/zh_cn.json':
            data = json.loads(raw)
            if data.get('item.eccentrictome.tome') != '怪奇宝典':
                data['item.eccentrictome.tome'] = '怪奇宝典'
                entries[index] = (info, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode())
                changed = True
    target.parent.mkdir(parents=True, exist_ok=True)
    if not changed:
        if source.resolve() != target.resolve():
            target.write_bytes(source.read_bytes())
        return
    temporary = target.with_name(target.name + '.tmp')
    with zipfile.ZipFile(temporary, 'w') as archive:
        archive.comment = comment
        for info, raw in entries:
            archive.writestr(info, raw)
    temporary.replace(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--template', type=Path, default=PROJECT / 'tools/guide-tome/GuideTome.js')
    args = parser.parse_args()
    books = catalog(args.instance)
    output = args.output
    (output / 'kubejs/server_scripts/expedition').mkdir(parents=True, exist_ok=True)
    (output / 'kubejs/guide-tome-catalog.json').write_text(
        json.dumps(books, ensure_ascii=False, indent=2) + '\n')
    (output / 'kubejs/server_scripts/expedition/GuideTome.js').write_bytes(args.template.read_bytes())
    config = (args.instance / 'config/eccentrictome-common.toml').read_text()
    whitelist = tomllib.loads(config)['common']['items']
    # The advanced Malum volume is attachable after its native acquisition.
    whitelist = list(dict.fromkeys(whitelist + [book['id'] for book in books] + ['malum:encyclopedia_esoterica']))
    config = re.sub(r'(?m)^(\s*items\s*=).+$',
                    lambda match: match[1] + ' ' + json.dumps(whitelist, ensure_ascii=False), config)
    (output / 'config').mkdir(parents=True, exist_ok=True)
    (output / 'config/eccentrictome-common.toml').write_text(config)
    patched = []
    for folder in ['config/paxi/resourcepacks', 'resourcepacks']:
        for source in sorted((args.instance / folder).glob('*Chinese-pack*.zip')):
            with zipfile.ZipFile(source) as archive:
                if 'assets/eccentrictome/lang/zh_cn.json' not in archive.namelist():
                    continue
            relative = source.relative_to(args.instance)
            restore_name(source, output / relative)
            patched.append(relative.as_posix())
    print(json.dumps({'books': len(books), 'nameRestoredIn': patched}, ensure_ascii=False))


if __name__ == '__main__':
    main()
