"""Scale current dedicated-server generation settings without touching any worlds.

The report directory records configuration files only. Reusing a completed report
is idempotent; use a fresh report directory for a separate scaling operation.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import re

ROOT = Path(__file__).resolve().parent
FILES = (
    'config/tectonic.json',
    'config/sparsestructures.json5',
    'config/terrablender.toml',
    'config/cso-common.toml',
    'config/expedition-boss-density.json',
    'kubejs/data/minecraft/worldgen/structure_set/strongholds.json',
)
NOISE_KEYS = (
    ('biomes', 'temperature_scale'), ('biomes', 'vegetation_scale'),
    ('continents', 'continents_scale'), ('continents', 'erosion_scale'),
    ('continents', 'ridge_scale'), ('islands', 'noise_scale'),
)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def formatted(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def scaled_files(before, factor):
    """Return validated generation settings derived solely from current files."""
    result = {}
    tectonic = json.loads(before[FILES[0]])
    for section, key in NOISE_KEYS:
        tectonic[section][key] /= factor
        if not math.isfinite(tectonic[section][key]) or tectonic[section][key] <= 0:
            raise ValueError(f'Invalid Tectonic scale: {section}.{key}')
    result[FILES[0]] = formatted(tectonic)

    sparse = json.loads(before[FILES[1]])
    sparse['spreadFactor'] *= factor
    for entry in sparse.get('customSpreadFactors', []):
        entry['factor'] *= factor
    if sparse['spreadFactor'] <= 0:
        raise ValueError('Sparse Structures spreadFactor must remain positive')
    result[FILES[1]] = formatted(sparse)

    zoom_delta = math.log2(factor)
    if not math.isclose(zoom_delta, round(zoom_delta), abs_tol=1e-9):
        raise ValueError('Use a power-of-two factor for an exact TerraBlender region change')
    terra = before[FILES[2]].decode()
    match = re.search(r'(?m)^(\s*overworld_region_size\s*=\s*)(\d+)', terra)
    if not match:
        raise ValueError('Missing TerraBlender overworld_region_size')
    region = int(match[2]) + round(zoom_delta)
    if not 2 <= region <= 6:
        raise ValueError(f'TerraBlender region size {region} is outside supported range 2–6')
    result[FILES[2]] = (terra[:match.start(2)] + str(region) + terra[match.end(2):]).encode()

    cso = before[FILES[3]].decode()
    keys = re.findall(r'(?m)^\s*((?:overworld|nether)_(?:spacing|separation))\s*=\s*(\d+)', cso)
    if len(keys) != 4:
        raise ValueError('Expected four CSO spacing/separation settings')
    new_values = {key: max(1 if key.endswith('spacing') else 0,
                           math.floor(int(value) * factor + 0.5)) for key, value in keys}
    for dimension in ('overworld', 'nether'):
        spacing = new_values[dimension + '_spacing']
        new_values[dimension + '_separation'] = min(new_values[dimension + '_separation'], spacing - 1)
    result[FILES[3]] = re.sub(
        r'(?m)^(\s*)((?:overworld|nether)_(?:spacing|separation))(\s*=\s*)(\d+)',
        lambda match: match[1] + match[2] + match[3] + str(new_values[match[2]]), cso).encode()

    boss = json.loads(before[FILES[4]])
    for key, value in boss['twilightLandmarkFrequencies'].items():
        value /= factor * factor
        if not 0 < value <= 1:
            raise ValueError(f'Twilight frequency for {key} would exceed the valid range')
        boss['twilightLandmarkFrequencies'][key] = value
    result[FILES[4]] = formatted(boss)

    strongholds = json.loads(before[FILES[5]])
    placement = strongholds['placement']
    if placement['type'] != 'minecraft:concentric_rings':
        raise ValueError('Expected native concentric-ring strongholds')
    placement['distance'] = max(1, math.floor(placement['distance'] * factor + 0.5))
    result[FILES[5]] = formatted(strongholds)
    return result


def finish_application(report, report_dir, dry_run):
    """Resume a prepared operation only when every file is before or after."""
    instance, deployment = Path(report['instance']), Path(report['deployment'])
    for row in report['files']:
        for root in (instance, deployment):
            target = root / row['path']
            current = digest(target.read_bytes()) if target.exists() else None
            previous = row['beforeSha256'] if root == instance else row['deploymentBeforeSha256']
            accepted = {row['afterSha256']} if report['status'] == 'applied' else {previous, row['afterSha256']}
            if current not in accepted:
                raise RuntimeError(f'Configuration differs from the recorded operation: {target}')
    if report['status'] == 'applied' or dry_run:
        return
    payloads = {row['path']: (report_dir / 'after-config' / row['path']).read_bytes()
                for row in report['files']}
    for row in report['files']:
        if digest(payloads[row['path']]) != row['afterSha256']:
            raise RuntimeError(f'Recorded target configuration changed: {row["path"]}')
    for name, blob in payloads.items():
        for root in (instance, deployment):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
    report['status'] = 'applied'
    (report_dir / 'local-config-scale.json').write_bytes(formatted(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factor', type=float, default=0.5,
                        help='Linear scale relative to current settings (default: 0.5)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--instance', type=Path, default=ROOT / 'instance')
    parser.add_argument('--deployment', type=Path, default=ROOT / 'deployment')
    parser.add_argument('--report-dir', type=Path, default=ROOT / 'evidence/half-scale-reset-20261017')
    args = parser.parse_args()
    if not math.isfinite(args.factor) or args.factor <= 0:
        parser.error('--factor must be finite and positive')
    instance, deployment = args.instance.resolve(), args.deployment.resolve()
    report_dir = args.report_dir.resolve()
    receipt = report_dir / 'local-config-scale.json'
    if receipt.exists():
        report = json.loads(receipt.read_text())
        if (report['relativeLinearFactor'] != args.factor or report['instance'] != str(instance)
                or report['deployment'] != str(deployment)):
            raise RuntimeError('This report belongs to a different operation; select a fresh --report-dir')
        was_applied = report['status'] == 'applied'
        finish_application(report, report_dir, args.dry_run)
        print(json.dumps({'status': 'already-applied' if was_applied else report['status'], 'report': str(receipt),
                          'relativeLinearFactor': args.factor, 'worldsTouched': False}, indent=2))
        return

    before = {name: (instance / name).read_bytes() for name in FILES}
    for name in FILES:
        override = deployment / name
        if override.exists() and override.read_bytes() != before[name]:
            raise RuntimeError(f'Instance and deployment disagree; reconcile before scaling: {name}')
    after = scaled_files(before, args.factor)
    report = {
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'basis': 'Current dedicated-server files; no historical baseline substituted',
        'relativeLinearFactor': args.factor,
        'instance': str(instance), 'deployment': str(deployment),
        'status': 'dry-run' if args.dry_run else 'prepared',
        'worldsTouched': False, 'worldBackupsCreated': False,
        'configSnapshotOnly': True,
        'limits': [
            'Sparse Structures rounds integer grids; tiny grids may not halve exactly.',
            'Native fixed landmark layouts remain native; Twilight boss candidate frequencies are scaled.',
            'Biome frequency and TerraBlender regions change distribution, not exact biome outlines.',
            'Nether TerraBlender regions retain their current setting.',
        ],
        'files': [{'path': name, 'beforeSha256': digest(before[name]),
                   'afterSha256': digest(after[name]),
                   'deploymentBeforeSha256': digest(before[name]) if (deployment / name).exists() else None}
                  for name in FILES],
    }
    if not args.dry_run:
        for name in FILES:
            snapshot = report_dir / 'before-config' / name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(before[name])
            desired = report_dir / 'after-config' / name
            desired.parent.mkdir(parents=True, exist_ok=True)
            desired.write_bytes(after[name])
        # Write the operation plan before settings so an interruption can resume.
        receipt.write_bytes(formatted(report))
        finish_application(report, report_dir, False)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
