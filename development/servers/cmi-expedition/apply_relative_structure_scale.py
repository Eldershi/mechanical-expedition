"""Scale current dedicated-server structure spacing without changing biomes or worlds.

Only the four structure configuration files below can be written. A configuration
receipt makes a completed operation idempotent; use a new report directory for a
new operation. No world data is read, copied, archived, or deleted here.
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
    'config/sparsestructures.json5',
    'config/cso-common.toml',
    'config/expedition-boss-density.json',
    'kubejs/data/minecraft/worldgen/structure_set/strongholds.json',
)


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def formatted(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def protected_hashes(instance, deployment):
    """Record all other config/KubeJS files, including biome and terrain inputs."""
    result = {}
    for label, root in (('instance', instance), ('deployment', deployment)):
        result[label] = {}
        for directory in ('config', 'kubejs'):
            for path in sorted((root / directory).rglob('*')):
                if path.is_file() and path.relative_to(root).as_posix() not in FILES:
                    result[label][path.relative_to(root).as_posix()] = digest(path.read_bytes())
    return result


def scaled_files(before, factor):
    result = {}
    sparse = json.loads(before[FILES[0]])
    sparse['spreadFactor'] *= factor
    for entry in sparse.get('customSpreadFactors', []):
        entry['factor'] *= factor
    for value in [sparse['spreadFactor']] + [row['factor'] for row in sparse.get('customSpreadFactors', [])]:
        if not math.isfinite(value) or value <= 0:
            raise ValueError('Sparse Structures spread factors must remain finite and positive')
    result[FILES[0]] = formatted(sparse)

    cso = before[FILES[1]].decode()
    keys = re.findall(r'(?m)^\s*((?:overworld|nether)_(?:spacing|separation))\s*=\s*(\d+)', cso)
    if len(keys) != 4 or len(dict(keys)) != 4:
        raise ValueError('Expected four distinct CSO spacing/separation settings')
    new_values = {key: max(1 if key.endswith('spacing') else 0,
                           math.floor(int(value) * factor + 0.5)) for key, value in keys}
    for dimension in ('overworld', 'nether'):
        spacing = new_values[dimension + '_spacing']
        new_values[dimension + '_separation'] = min(new_values[dimension + '_separation'], spacing - 1)
    result[FILES[1]] = re.sub(
        r'(?m)^(\s*)((?:overworld|nether)_(?:spacing|separation))(\s*=\s*)(\d+)',
        lambda match: match[1] + match[2] + match[3] + str(new_values[match[2]]), cso).encode()

    boss = json.loads(before[FILES[2]])
    for key, value in boss['twilightLandmarkFrequencies'].items():
        value /= factor * factor
        if not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError(f'Twilight frequency for {key} is outside (0, 1]')
        boss['twilightLandmarkFrequencies'][key] = value
    result[FILES[2]] = formatted(boss)

    strongholds = json.loads(before[FILES[3]])
    placement = strongholds['placement']
    if placement['type'] != 'minecraft:concentric_rings':
        raise ValueError('Expected native concentric-ring strongholds')
    placement['distance'] = max(1, math.floor(placement['distance'] * factor + 0.5))
    result[FILES[3]] = formatted(strongholds)
    return result


def finish_application(report, report_dir, dry_run):
    instance, deployment = Path(report['instance']), Path(report['deployment'])
    if protected_hashes(instance, deployment) != report['protectedConfigHashes']:
        raise RuntimeError('A non-structure config/KubeJS file changed since this operation was prepared')
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
    if protected_hashes(instance, deployment) != report['protectedConfigHashes']:
        raise RuntimeError('A non-structure config/KubeJS file changed during application')
    report['status'] = 'applied'
    (report_dir / 'local-structure-scale.json').write_bytes(formatted(report))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--factor', type=float, default=1.5,
                        help='Linear structure distance relative to current settings (default: 1.5)')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--instance', type=Path, default=ROOT / 'instance')
    parser.add_argument('--deployment', type=Path, default=ROOT / 'deployment')
    parser.add_argument('--report-dir', type=Path, default=ROOT / 'evidence/structure150-reset-20261017')
    args = parser.parse_args()
    if not math.isfinite(args.factor) or args.factor <= 0:
        parser.error('--factor must be finite and positive')
    instance, deployment = args.instance.resolve(), args.deployment.resolve()
    report_dir = args.report_dir.resolve()
    receipt = report_dir / 'local-structure-scale.json'
    if receipt.exists():
        report = json.loads(receipt.read_text())
        if (report['relativeStructureDistanceFactor'] != args.factor or report['instance'] != str(instance)
                or report['deployment'] != str(deployment)):
            raise RuntimeError('This report belongs to a different operation; select a fresh --report-dir')
        was_applied = report['status'] == 'applied'
        finish_application(report, report_dir, args.dry_run)
        print(json.dumps({'status': 'already-applied' if was_applied else report['status'],
                          'report': str(receipt), 'relativeStructureDistanceFactor': args.factor,
                          'biomeTerrainConfigsUnchanged': True, 'worldsTouched': False}, indent=2))
        return

    before = {name: (instance / name).read_bytes() for name in FILES}
    for name in FILES:
        override = deployment / name
        if not override.exists() or override.read_bytes() != before[name]:
            raise RuntimeError(f'Instance and deployment disagree; reconcile before scaling: {name}')
    protected = protected_hashes(instance, deployment)
    after = scaled_files(before, args.factor)
    report = {
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'basis': 'Current dedicated-server structure settings; biome and terrain settings preserved',
        'relativeStructureDistanceFactor': args.factor,
        'instance': str(instance), 'deployment': str(deployment),
        'status': 'dry-run' if args.dry_run else 'prepared',
        'worldsTouched': False, 'worldBackupsCreated': False, 'configSnapshotOnly': True,
        'biomeTerrainConfigsUnchanged': True,
        'limits': [
            'Sparse Structures rounds integer grids; small spacing grids may not scale exactly.',
            'Native Twilight landmark layout is retained; candidate frequencies scale by inverse area.',
            'Stronghold ring count and spread remain unchanged; only ring distance is scaled.',
        ],
        'files': [{'path': name, 'beforeSha256': digest(before[name]),
                   'afterSha256': digest(after[name]), 'deploymentBeforeSha256': digest(before[name])}
                  for name in FILES],
        'protectedConfigHashes': protected,
    }
    if not args.dry_run:
        for name in FILES:
            snapshot = report_dir / 'before-config' / name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(before[name])
            desired = report_dir / 'after-config' / name
            desired.parent.mkdir(parents=True, exist_ok=True)
            desired.write_bytes(after[name])
        receipt.write_bytes(formatted(report))
        finish_application(report, report_dir, False)
    summary = {key: value for key, value in report.items() if key != 'protectedConfigHashes'}
    summary['protectedFileCounts'] = {key: len(value) for key, value in protected.items()}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
