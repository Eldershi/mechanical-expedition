"""Repair MutantMore 2.0.0's dedicated-server map enum registration.

Only mutantmore.mixins.json changes. The upstream JAR remains unmodified in the
client instance; a stopped dedicated server must be used for runtime deployment.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import io
import json
import os
import shutil
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
JAR_NAME = 'mutantmore-1.20.1-early_access-2.0.0.jar'
UPSTREAM_SHA256 = '8cc7dc53ce0b7f5a0290a96e4cce210accc1f479a8c5ccbd8ae21fbfa8cb1f31'
CONFIG = 'mutantmore.mixins.json'
MIXIN = 'MapDecorationTypeMixin'
MIXIN_CLASS = 'com/alexander/mutantmore/mixin/MapDecorationTypeMixin.class'


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def patch_server_jar(jar, evidence_dir):
    jar, evidence_dir = Path(jar), Path(evidence_dir)
    original = jar.read_bytes()
    source_sha = digest(original)
    with zipfile.ZipFile(io.BytesIO(original)) as before:
        infos = before.infolist()
        names = before.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Duplicate ZIP member names are not supported')
        if any(n.upper().startswith('META-INF/') and n.upper().endswith(('.SF', '.RSA', '.DSA', '.EC')) for n in names):
            raise ValueError('Refusing to alter a signed JAR')
        members = {name: before.read(name) for name in names}
        archive_comment = before.comment
    config = json.loads(members[CONFIG])
    client, common = config['client'], config['mixins']
    if client.count(MIXIN) == 0 and common.count(MIXIN) == 1:
        # An unchanged second invocation must leave the exact archive bytes alone.
        manifest_path = evidence_dir / 'integrity-manifest.json'
        if manifest_path.is_file():
            previous = json.loads(manifest_path.read_text())
            if previous['patchedJarSha256'] != source_sha:
                raise ValueError('Previously patched JAR no longer matches its manifest')
            return previous
        raise ValueError('JAR appears patched but has no matching integrity manifest')
    if source_sha != UPSTREAM_SHA256:
        raise ValueError(f'Unexpected upstream JAR SHA-256: {source_sha}')
    if client.count(MIXIN) != 1 or common.count(MIXIN) != 0:
        raise ValueError('Unexpected MutantMore mixin registration')
    moved_class = members[MIXIN_CLASS]
    forbidden = [b'net/minecraft/client/', b'com/mojang/blaze3d/']
    if any(reference in moved_class for reference in forbidden):
        raise ValueError('Moved mixin contains a client-only class reference')

    patched_config = copy.deepcopy(config)
    patched_config['client'].remove(MIXIN)
    patched_config['mixins'].append(MIXIN)
    # Prove no unrelated JSON setting or mixin order was altered.
    restored_config = copy.deepcopy(patched_config)
    restored_config['mixins'].remove(MIXIN)
    restored_config['client'].insert(client.index(MIXIN), MIXIN)
    assert restored_config == config
    output_members = dict(members)
    output_members[CONFIG] = (json.dumps(patched_config, indent=2) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as after:
        after.comment = archive_comment
        for info in infos:
            after.writestr(copy.copy(info), output_members[info.filename])
    patched = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(patched)) as after:
        assert after.testzip() is None
        assert after.namelist() == names
        changed = [n for n in names if after.read(n) != members[n]]
        assert changed == [CONFIG], changed
        assert all(after.getinfo(n).date_time == i.date_time for n, i in zip(names, infos))
        member_evidence = [
            {'path': n, 'beforeSha256': digest(members[n]),
             'afterSha256': digest(after.read(n)), 'unchanged': n != CONFIG}
            for n in names
        ]

    evidence_dir.mkdir(parents=True, exist_ok=True)
    backup = evidence_dir / 'original' / JAR_NAME
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists() and backup.read_bytes() != original:
        raise ValueError('Existing original JAR backup differs; refusing to overwrite')
    if not backup.exists():
        shutil.copy2(jar, backup)
    (evidence_dir / 'original' / CONFIG).write_bytes(members[CONFIG])
    (evidence_dir / 'patched-mutantmore.mixins.json').write_bytes(output_members[CONFIG])
    manifest = {
        'patch': 'Register MutantMore MapDecorationTypeMixin on both client and dedicated server',
        'scope': 'Dedicated server JAR only; client JAR and class bytecode unchanged',
        'jarFile': jar.name,
        'upstreamJarSha256': source_sha,
        'patchedJarSha256': digest(patched),
        'changedZipMembers': changed,
        'zipIntegrityPassed': True,
        'unchangedZipMemberCount': len(names) - 1,
        'movedMixinClassSha256': digest(moved_class),
        'movedMixinHasNoMinecraftClientOrBlaze3dReferences': True,
        'mixinMoveIsOnlyJsonSemanticChange': True,
        'originalJarBackup': str(backup.resolve()),
        'members': member_evidence,
    }
    # Complete integrity checks before replacing the local dedicated-server JAR.
    with tempfile.NamedTemporaryFile(dir=jar.parent, prefix='.mutantmore-', delete=False) as temporary:
        temporary.write(patched)
        temporary_path = Path(temporary.name)
    try:
        shutil.copymode(jar, temporary_path)
        os.replace(temporary_path, jar)
    finally:
        temporary_path.unlink(missing_ok=True)
    write_json(evidence_dir / 'integrity-manifest.json', manifest)
    return manifest


def update_selection(selection_path, manifest):
    selection_path = Path(selection_path)
    selection = json.loads(selection_path.read_text())
    row = next(r for r in selection['included'] if r['file'] == JAR_NAME)
    if row['sha256'] not in {manifest['upstreamJarSha256'], manifest['patchedJarSha256']}:
        raise ValueError('Mod-selection hash does not match either known JAR')
    row.setdefault('upstreamSha256', manifest['upstreamJarSha256'])
    row['sha256'] = manifest['patchedJarSha256']
    row['patch'] = 'patch_mutantmore_server.py: MapDecorationTypeMixin moved to common mixins'
    write_json(selection_path, selection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--jar', type=Path, default=ROOT / 'instance/mods' / JAR_NAME)
    parser.add_argument('--evidence-dir', type=Path, default=ROOT / 'evidence/mutantmore-server-fix')
    parser.add_argument('--selection', type=Path)
    parser.add_argument('--stage-root', type=Path, help='Copy the patched JAR to this upload root under mods/')
    args = parser.parse_args()
    result = patch_server_jar(args.jar, args.evidence_dir)
    if args.selection:
        update_selection(args.selection, result)
    if args.stage_root:
        staged = args.stage_root / 'mods' / JAR_NAME
        staged.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(args.jar, staged)
        assert digest(staged.read_bytes()) == result['patchedJarSha256']
    print(json.dumps({k: v for k, v in result.items() if k != 'members'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
