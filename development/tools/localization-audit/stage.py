#!/usr/bin/env python3
"""Stage the Chinese supplement, native tooltip translations and pack order."""

import argparse
import json
from pathlib import Path
import re
import shutil

from build import build


HERE = Path(__file__).resolve().parent
PACK = 'Expedition-Chinese-Supplement.zip'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--include-options', action='store_true')
    args = parser.parse_args()
    output = args.output
    result = build(HERE / 'translations', output / 'config/paxi/resourcepacks' / PACK)
    literals = {'exact': {}, 'patterns': [], 'allowlist': {}}
    for name in ['literal-translations.json', 'literal-extra-translations.json']:
        source = HERE / name
        if source.exists():
            part = json.loads(source.read_text())
            literals['exact'].update(part['exact'])
            literals['patterns'].extend(part.get('patterns', []))
            literals['allowlist'].update(part.get('allowlist', {}))
    config = output / 'kubejs/config/expedition-literal-translations.json'
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(json.dumps(literals, ensure_ascii=False, indent=2) + '\n')
    script = output / 'kubejs/client_scripts/expedition/ChineseTooltips.js'
    script.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / 'ChineseTooltips.js', script)
    startup = output / 'kubejs/startup_scripts/expedition/ChineseTooltipEvents.js'
    startup.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / 'ChineseTooltipEvents.js', startup)
    relative = 'config/paxi/resourcepack_load_order.json'
    order = json.loads((args.instance / relative).read_text())
    order['loadOrder'] = [name for name in order['loadOrder'] if name != PACK] + [PACK]
    (output / relative).write_text(json.dumps(order, ensure_ascii=False, indent=2) + '\n')
    if args.include_options:
        options = (args.instance / 'options.txt').read_text()
        line = next(line for line in options.splitlines() if line.startswith('resourcePacks:'))
        packs = json.loads(line.split(':', 1)[1])
        packs = [name for name in packs if name.removeprefix('file/') != PACK] + [PACK]
        options = re.sub(r'(?m)^resourcePacks:.*$',
                         lambda match: 'resourcePacks:' + json.dumps(packs, ensure_ascii=False, separators=(',', ':')),
                         options)
        (output / 'options.txt').write_text(options)
    print(json.dumps(dict(result, literalEntries=len(literals['exact']),
                          literalPatterns=len(literals['patterns']))))


if __name__ == '__main__':
    main()
