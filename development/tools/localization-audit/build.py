#!/usr/bin/env python3
"""Build a deterministic Chinese supplement from reviewed and upstream resources."""

import argparse
import hashlib
import json
import re
from pathlib import Path
import zipfile


HERE = Path(__file__).resolve().parent


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def build(source, output):
    entries = {}
    languages = {}
    # Project translations take precedence over imported community resources.
    for layer in ['upstream', 'manual']:
        folder = source / layer
        for path in sorted((folder / 'assets').rglob('*')):
            if not path.is_file():
                continue
            relative = path.relative_to(folder).as_posix()
            if relative.endswith('/lang/zh_cn.json'):
                languages.setdefault(relative, {}).update(json.loads(path.read_text()))
            else:
                entries[relative] = path.read_bytes()
        for path in sorted(folder.glob('*.json')):
            if path.name in {'SOURCE.json', 'manifest.json', 'allowlist.json'}:
                continue
            values = json.loads(path.read_text())
            if not isinstance(values, dict) or any(not isinstance(value, str) for value in values.values()):
                raise ValueError('Language source must map keys to strings: ' + path.name)
            relative = 'assets/' + path.stem + '/lang/zh_cn.json'
            languages.setdefault(relative, {}).update(values)
        if layer == 'upstream':
            for name in ['SOURCE.json', 'LICENSE-CFPA.txt']:
                if (folder / name).exists():
                    entries['credits/' + name] = (folder / name).read_bytes()
    # Restore the searchable item name regardless of earlier pack overrides.
    languages.setdefault('assets/eccentrictome/lang/zh_cn.json', {}).update({
        'item.eccentrictome.tome': '怪奇宝典',
        'eccentrictome.name': '怪奇宝典 (%s)',
    })
    for name in ['literal-translations.json', 'literal-extra-translations.json']:
        path = source.parent / name
        if path.exists():
            values = json.loads(path.read_text()).get('languageKeys', {})
            languages.setdefault('assets/expedition/lang/zh_cn.json', {}).update(values)
    for relative, values in languages.items():
        languages[relative] = {key: value for key, value in values.items()
                               if not re.match(r"^_+comment", key, re.IGNORECASE)}
        entries[relative] = encoded(languages[relative])
    entries['pack.mcmeta'] = encoded({'pack': {
        'pack_format': 15, 'description': '机械动力：远征 · 中文补全',
    }})
    entries['credits/README.txt'] = (
        'Mechanical Expedition Chinese supplement\n'
        'Selected community translations: CFPA team and contributors.\n'
        'https://github.com/CFPAOrg/Minecraft-Mod-Language-Package\n'
        'Community material is licensed under CC BY-NC-SA 4.0; see LICENSE-CFPA.txt.\n'
        'Additional translations were prepared for Mechanical Expedition.\n'
    ).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + '.tmp')
    with zipfile.ZipFile(temporary, 'w') as archive:
        for relative, data in sorted(entries.items()):
            info = zipfile.ZipInfo(relative, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data, compresslevel=9)
    temporary.replace(output)
    return {'languageEntries': sum(map(len, languages.values())), 'resources': len(entries),
            'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=HERE / 'translations')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output)))


if __name__ == '__main__':
    main()
