"""Adapt MBTool 1.0.28's single legacy mouse field to JEMM 4.27.

Only one UTF-8 constant in one class changes. All bytecode instructions,
attributes, resources, mixin registrations, and other ZIP members are retained.
Build and inspect the staged artifact before using --deploy. A client restart
is required; this does not modify classes in a running JVM.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import io
import json
import os
import shutil
import struct
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'evidence/crash-20261018-010722'
JAR_NAME = 'MultiBuilderTool-1.20.1-1.0.28.jar'
SOURCE_SHA256 = '7cec772660c8e601c2708c6288ff6e12014ffd1c62208e8ffc8519724ee38e5e'
CLASS = 'igentuman/mbtool/mixin/MultiblockWidgetMixin.class'
OWNER = 'giselle/jei_mekanism_multiblocks/client/JEI_MekanismMultiblocks_Client'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pool(blob):
    assert blob[:4] == b'\xca\xfe\xba\xbe'
    count = struct.unpack_from('>H', blob, 8)[0]
    entries, index, offset = {}, 1, 10
    fixed = {3: 4, 4: 4, 5: 8, 6: 8, 7: 2, 8: 2, 9: 4, 10: 4,
             11: 4, 12: 4, 15: 3, 16: 2, 17: 4, 18: 4, 19: 2, 20: 2}
    while index < count:
        start = offset
        tag = blob[offset]
        offset += 1
        if tag == 1:
            length = struct.unpack_from('>H', blob, offset)[0]
            offset += 2
            value = blob[offset:offset + length]
            offset += length
        else:
            if tag not in fixed:
                raise ValueError(f'Unknown constant pool tag {tag}')
            value = blob[offset:offset + fixed[tag]]
            offset += fixed[tag]
        entries[index] = (tag, value, start, offset)
        index += 2 if tag in (5, 6) else 1
    return entries, offset


def fields(entries):
    def utf(index):
        assert entries[index][0] == 1
        return entries[index][1].decode('utf-8')
    result = []
    for index, (tag, data, _, _) in entries.items():
        if tag != 9:
            continue
        owner_index, pair_index = struct.unpack('>HH', data)
        assert entries[owner_index][0] == 7 and entries[pair_index][0] == 12
        name_index, type_index = struct.unpack('>HH', entries[pair_index][1])
        owner = utf(struct.unpack('>H', entries[owner_index][1])[0])
        result.append((owner, utf(name_index), utf(type_index), name_index))
    return result


def patched_class(blob):
    before, body_start = pool(blob)
    matches = [f for f in fields(before) if f[:3] == (OWNER, 'PRESSED', 'Z')]
    assert len(matches) == 1, matches
    entry_index = matches[0][3]
    tag, old_value, start, end = before[entry_index]
    assert tag == 1 and old_value == b'PRESSED'
    new_value = b'MOUSE_PRESSED'
    result = blob[:start] + b'\x01' + struct.pack('>H', len(new_value)) + new_value + blob[end:]
    after, after_body_start = pool(result)
    assert before.keys() == after.keys()
    changed = [i for i in before if before[i][:2] != after[i][:2]]
    assert changed == [entry_index]
    assert blob[body_start:] == result[after_body_start:]
    assert [f for f in fields(after) if f[:3] == (OWNER, 'MOUSE_PRESSED', 'Z')]
    return result, entry_index


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT / 'instance/mods' / JAR_NAME)
    parser.add_argument('--evidence-dir', type=Path, default=EVIDENCE)
    parser.add_argument('--deploy', action='store_true')
    options = parser.parse_args()
    target, evidence = options.source.resolve(), options.evidence_dir.resolve()
    original = target.read_bytes()
    manifest_path = evidence / 'patch-manifest.json'
    if manifest_path.exists():
        previous = json.loads(manifest_path.read_text())
        if sha(original) == previous['patchedJarSha256']:
            print('Matching patch already deployed; no changes made.')
            return
    if sha(original) != SOURCE_SHA256:
        raise ValueError('Unexpected original JAR; refusing an unverified patch')
    with zipfile.ZipFile(io.BytesIO(original)) as source:
        infos = source.infolist()
        names = source.namelist()
        assert len(names) == len(set(names))
        assert not any(n.upper().startswith('META-INF/') and n.upper().endswith(
            ('.SF', '.RSA', '.DSA', '.EC')) for n in names)
        members = {n: source.read(n) for n in names}
        comment = source.comment
    replacement, constant_index = patched_class(members[CLASS])
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as out:
        out.comment = comment
        for info in infos:
            out.writestr(copy.copy(info), replacement if info.filename == CLASS else members[info.filename])
    patched = buffer.getvalue()
    with zipfile.ZipFile(io.BytesIO(patched)) as check:
        assert check.testzip() is None
        assert check.namelist() == names
        changed = [n for n in names if check.read(n) != members[n]]
        assert changed == [CLASS], changed
    backup = evidence / 'original' / JAR_NAME
    staged = evidence / 'patched' / JAR_NAME
    for path in (backup, staged):
        path.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists() and backup.read_bytes() != original:
        raise ValueError('Original backup differs; refusing to overwrite it')
    if not backup.exists():
        shutil.copy2(target, backup)
    staged.write_bytes(patched)
    manifest = {
        'sourceJarSha256': sha(original), 'patchedJarSha256': sha(patched),
        'sourceClassSha256': sha(members[CLASS]), 'patchedClassSha256': sha(replacement),
        'changedZipMembers': changed, 'unchangedZipMembers': len(names) - 1,
        'changedUtf8ConstantIndex': constant_index, 'classBodyUnchanged': True,
        'fieldOwner': OWNER, 'oldField': 'PRESSED:Z', 'newField': 'MOUSE_PRESSED:Z',
        'backup': str(backup), 'stagedJar': str(staged), 'deployed': False,
        'runtimeClientRestartRequired': True,
        'scope': 'MBTool input compatibility only; no mod, mixin or feature removed'
    }
    if options.deploy:
        assert target.read_bytes() == original, 'Target changed during staging'
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.mbtool-', delete=False) as temp:
            temp.write(patched)
            temporary = Path(temp.name)
        try:
            shutil.copymode(target, temporary)
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        assert sha(target.read_bytes()) == sha(patched)
        manifest['deployed'] = True
        manifest['deployedPath'] = str(target)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
