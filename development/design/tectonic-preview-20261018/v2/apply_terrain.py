#!/usr/bin/env python3
"""Prepare only the fresh, isolated v2 preview. Never alter generated worlds."""
from pathlib import Path
import datetime
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
INSTANCE = ROOT / 'clients/cmi-expedition/tectonic-preview-v2/instance'
OUT = Path(__file__).resolve().parent / 'terrain'


def main():
    assert INSTANCE.is_dir() and INSTANCE.resolve().is_relative_to(ROOT.resolve())
    assert not (INSTANCE / 'saves').exists(), 'Refuse terrain changes after world creation'
    marker = INSTANCE / '.tectonic-v2-terrain.json'
    assert not marker.exists(), 'Refuse repeat application'
    OUT.mkdir(exist_ok=True)
    backups = OUT / 'before'
    changes = []

    def change(rel, transform):
        path = INSTANCE / rel
        before = path.read_bytes()
        data = json.loads(before)
        transform(data)
        after = (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode()
        backup = backups / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(before)
        tmp = path.with_suffix(path.suffix + '.v2-tmp')
        tmp.write_bytes(after)
        tmp.replace(path)
        changes.append({'file':rel,'beforeSha256':hashlib.sha256(before).hexdigest(),
                        'afterSha256':hashlib.sha256(after).hexdigest()})

    def terrain(d):
        d['global_terrain'].update(elevation_boost=0.0, vertical_scale=1.0,
                                   max_y=384, min_y=-64)
        d['continents'].update(continents_scale=.17, erosion_scale=.18, ridge_scale=.20)
        d['biomes'].update(temperature_scale=.24, vegetation_scale=.24,
                           vegetation_offset=-.10)

    change('config/tectonic.json', terrain)
    change('kubejs/data/minecraft/worldgen/noise_settings/overworld.json',
           lambda d:d['noise'].update(min_y=-64,height=448))
    change('kubejs/data/minecraft/dimension_type/overworld.json',
           lambda d:d.update(min_y=-64,height=448,logical_height=448))
    options = INSTANCE / 'options.txt'
    lines = options.read_text().splitlines()
    lines = ['simulationDistance:4' if s.startswith('simulationDistance:') else s for s in lines]
    options.write_text('\n'.join(lines)+'\n')
    result = {'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'instance':str(INSTANCE),'changes':changes,
              'goal':'Approximately halve peak-to-foothill relief; preserve compact travel scale and wider mountain transitions',
              'heightTarget':'Candidate peaks around Y250–300; requires native sampling, not guaranteed',
              'snowAndTreeline':'Installed separately by v2 climate compatibility module',
              'structurePlacement':'Installed separately via verified Lithostitched 1.4.11 modifiers',
              'vegetation':'Inherited 271 tree-root rarity filters from v1; climate layer adds an alpine treeline',
              'notCopied':'Any existing save, Xaero/DH database, Chunky task or exported world data'}
    marker.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (OUT/'applied.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
