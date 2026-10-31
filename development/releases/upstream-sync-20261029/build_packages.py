#!/usr/bin/env python3
"""Build a minimal client delta after the parent finishes runtime validation.

Final builds require explicit passing --validation-report JSON files. --preview
may create a review-only package, whose manifest records that it is unvalidated.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

import install_client as installer


def build(release, staging=None, before_path=None, output=None, validation_reports=(), preview=False):
    release = Path(release).absolute()
    staging = Path(staging).absolute() if staging else release / 'staging'
    before_path = Path(before_path).absolute() if before_path else release / 'evidence/active-before.json'
    output = Path(output).absolute() if output else release
    before = installer.read_json(before_path)['files']
    reports = []
    if not validation_reports and not preview:
        raise installer.PatchError('Final build requires passing --validation-report files; use --preview only for review.')
    for report_path in validation_reports:
        report_path = Path(report_path).absolute()
        report = installer.read_json(report_path)
        if report.get('passed') is not True:
            raise installer.PatchError('Validation report has not passed: ' + str(report_path))
        reports.append({'path': str(report_path), 'sha256': installer.digest(report_path), 'passed': True})

    protected = {}
    for rel in installer.PROTECTED_CATALOGS:
        if rel not in before or not (staging / rel).is_file() or installer.digest(staging / rel) != before[rel]['sha256']:
            raise installer.PatchError('Protected restored catalog changed or disappeared: ' + rel)
        protected[rel] = before[rel]['sha256']

    # Updater changes are outside this integration and must not be silently
    # ignored: retaining the Expedition release channel is an explicit contract.
    for rel, row in before.items():
        if rel.startswith('updater/') and (not (staging / rel).is_file() or installer.digest(staging / rel) != row['sha256']):
            raise installer.PatchError('Expedition updater changed: ' + rel)

    after, excluded = {}, []
    for path in sorted(staging.rglob('*')):
        rel = path.relative_to(staging).as_posix()
        if path.is_symlink():
            raise installer.PatchError('Stage contains symbolic link: ' + rel)
        if not path.is_file():
            continue
        if not installer.eligible(rel):
            excluded.append(rel)
            continue
        after[rel] = {'sha256': installer.digest(path), 'bytes': path.stat().st_size}
    operations = []
    for rel in sorted(set(before) | set(after)):
        if not installer.eligible(rel) or rel in protected:
            continue
        old, new = before.get(rel), after.get(rel)
        old_hash, new_hash = (old or {}).get('sha256'), (new or {}).get('sha256')
        if old_hash == new_hash:
            continue
        operations.append({'path': rel, 'action': 'write' if new else 'delete',
                           'beforeSha256': old_hash, 'afterSha256': new_hash,
                           'bytes': (new or {}).get('bytes', 0)})
    manifest = {
        'schemaVersion': installer.SCHEMA, 'patchId': 'expedition-upstream-sync-20261029',
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'baseCommit': 'a87ff71c8aaeca32d3eab224d15994c70b1e7473',
        'upstreamCommit': '77f6e7adafa60007b34f464e8e810bd699649bdd',
        'validationStatus': 'preview_unvalidated' if preview else 'validated',
        'validationReports': reports, 'protectedCatalogs': protected,
        'operations': operations,
        'summary': {'writes': sum(op['action'] == 'write' for op in operations),
                    'deletes': sum(op['action'] == 'delete' for op in operations),
                    'payloadBytes': sum(op['bytes'] for op in operations),
                    'excludedStageFiles': len(excluded)},
    }
    installer.validate_manifest(manifest)
    output.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.client-package-', dir=output))
    try:
        payload = temporary / 'client-payload'
        payload.mkdir()
        for op in operations:
            if op['action'] != 'write':
                continue
            source = installer.safe_path(staging, op['path'])
            target = payload / op['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if installer.digest(target) != op['afterSha256']:
                raise installer.PatchError('Payload verification failed: ' + op['path'])
        installer.write_json(temporary / 'client-manifest.json', manifest)
        shutil.copy2(release / 'install_client.py', temporary / 'install_client.py')
        name = 'expedition-upstream-sync-20261029-client' + ('-preview' if preview else '') + '.zip'
        archive = temporary / name
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as z:
            z.write(temporary / 'install_client.py', 'install_client.py')
            z.write(temporary / 'client-manifest.json', 'client-manifest.json')
            for op in operations:
                if op['action'] == 'write':
                    z.write(payload / op['path'], 'client-payload/' + op['path'])
        # Build only owns these exact outputs; never remove the release folder.
        destination = output / 'client-payload'
        if destination.exists():
            if destination.is_symlink() or not destination.is_dir():
                raise installer.PatchError('Unsafe previous payload output')
            shutil.rmtree(destination)
        shutil.move(str(payload), destination)
        shutil.copy2(temporary / 'client-manifest.json', output / 'client-manifest.json')
        shutil.move(str(archive), output / name)
        result = {'passed': True, 'preview': preview, 'manifest': str(output / 'client-manifest.json'),
                  'archive': str(output / name), 'archiveSha256': installer.digest(output / name),
                  **manifest['summary']}
        evidence = release / 'evidence/client-package-build.json'
        installer.write_json(evidence, result)
        return result
    finally:
        shutil.rmtree(temporary, ignore_errors=True)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--release', type=Path, default=Path(__file__).resolve().parent)
    cli.add_argument('--staging', type=Path)
    cli.add_argument('--before', type=Path)
    cli.add_argument('--output', type=Path)
    cli.add_argument('--validation-report', type=Path, action='append', default=[])
    cli.add_argument('--preview', action='store_true')
    args = cli.parse_args()
    print(json.dumps(build(args.release, args.staging, args.before, args.output,
                           args.validation_report, args.preview), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    try:
        main()
    except (installer.PatchError, OSError, ValueError) as error:
        raise SystemExit(str(error))
