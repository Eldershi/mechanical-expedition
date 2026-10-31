"""Apply the requested world/render settings from the audited live-server baseline."""
from pathlib import Path
import argparse, json, re, shutil, zipfile
import math

PROJECT = Path(__file__).resolve().parents[3]
CLIENT = PROJECT / 'clients/cmi-expedition/instance'
SERVER = PROJECT / 'servers/cmi-expedition/instance'
EVIDENCE = PROJECT / 'servers/cmi-expedition/evidence/scale5-reset'
BACKUP = PROJECT / 'clients/cmi-expedition/backups/before-world-scale2-20261017'

def save(root, name, text):
    target = root / name
    old = BACKUP / ('client' if root == CLIENT else 'server') / name
    if target.exists() and not old.exists():
        old.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, old)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)

def formatted(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + '\n'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--server', action='store_true')
    parser.add_argument('--factor', type=int, choices=[2, 5], default=2)
    parser.add_argument('--report-dir', type=Path, default=PROJECT / 'clients/cmi-expedition/evidence/playtest-batch-20261017')
    args = parser.parse_args()
    factor = args.factor
    region_size = 3 + round(math.log2(factor))
    targets = [SERVER] if args.server else [CLIENT]
    tectonic = json.loads((EVIDENCE / 'remote-before-tectonic.json').read_text())
    scales = [('biomes', 'temperature_scale'), ('biomes', 'vegetation_scale'),
              ('continents', 'continents_scale'), ('continents', 'erosion_scale'),
              ('continents', 'ridge_scale'), ('islands', 'noise_scale')]
    for section, key in scales:
        tectonic[section][key] /= float(factor)
    sparse = json.loads((EVIDENCE / 'remote-before-sparsestructures.json5').read_text())
    sparse['spreadFactor'] *= float(factor)
    for entry in sparse['customSpreadFactors']:
        entry['factor'] *= float(factor)
    # Each additional TerraBlender zoom doubles linear region size.
    terra = (EVIDENCE / 'remote-before-terrablender.toml').read_text()
    terra = re.sub(r'overworld_region_size = \d+', f'overworld_region_size = {region_size}', terra)
    boss = json.loads((EVIDENCE / 'remote-before-expedition-boss-density.json').read_text())
    # Twilight's native fixed landmark grid ignores random-spread spacing. Thin
    # candidate density by factor^2 for the requested horizontal separation.
    boss['twilightLandmarkFrequencies'] = {
        key: value / float(factor * factor) for key, value in boss['twilightLandmarkFrequencies'].items()}
    # Sparse Structures intentionally skips concentric rings. Preserve Trek's
    # two stronghold variants/count, changing only their native ring distance.
    with zipfile.ZipFile(next((CLIENT / 'mods').glob('trek-*.jar'))) as archive:
        strongholds = json.loads(archive.read('data/minecraft/worldgen/structure_set/strongholds.json'))
    strongholds['placement']['distance'] *= factor
    files = {
        'config/tectonic.json': formatted(tectonic),
        'config/sparsestructures.json5': formatted(sparse),
        'config/terrablender.toml': terra,
        'config/expedition-boss-density.json': formatted(boss),
        'kubejs/data/minecraft/worldgen/structure_set/strongholds.json': formatted(strongholds),
    }
    # CSO replaces JSON placement after registry load, overriding Sparse Structures.
    cso = (EVIDENCE / 'remote-before-cso-common.toml').read_text()
    files['config/cso-common.toml'] = re.sub(
        r'((?:overworld|nether)_(?:spacing|separation)\s*=\s*)(\d+)',
        lambda match: match[1] + str(int(match[2]) * factor), cso)
    for root in targets:
        for name, text in files.items():
            save(root, name, text)
        properties = root / ('server.properties' if args.server else 'options.txt')
        text = properties.read_text()
        text = re.sub(r'(?m)^view-distance=\d+$', 'view-distance=12', text) if args.server else re.sub(
            r'(?m)^renderDistance:\d+$', 'renderDistance:12', text)
        save(root, properties.name, text)
    if not args.server:
        save(CLIENT, 'config/betterfpsdist.json', formatted({
            'verticalScaling': {'verticalScaling': 0.0},
            'horizontalScaling': {'horizontalScaling': 1.0},
            'affectEntities': {'affectEntities': False},
            'debugMode': {'debugMode': False},
        }))
        dh = (CLIENT / 'config/DistantHorizons.toml').read_text()
        dh = dh.replace('heightFogMixMode = "SPHERICAL"', 'heightFogMixMode = "CYLINDRICAL"')
        dh = dh.replace('heightFogMax = "1.0"', 'heightFogMax = "0.0"')
        save(CLIENT, 'config/DistantHorizons.toml', dh)
    report = {'basis': 'Actual live server configuration, audited before reset',
              'horizontalClimateAndTerrainScale': factor,
              'regionZoom': {'before': 3, 'after': region_size, 'linearFactor': 2 ** (region_size - 3),
                             'note': 'Region zoom and climate scale control distribution, not identical scaled copies of biome shapes.'},
              'randomStructureSpacingMultiplier': factor,
              'strongholdRingDistance': strongholds['placement']['distance'],
              'twilightCandidateFrequencyMultiplier': 1/(factor * factor),
              'vanillaRenderChunks': 12, 'dhLodChunks': 64,
              'verticalDistanceContribution': 0,
              'files': list(files), 'noWorldsDeletedByThisTool': True}
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / ('server-world-scale.json' if args.server else 'client-world-scale.json')).write_text(formatted(report))
    print(formatted(report))

if __name__ == '__main__':
    main()
