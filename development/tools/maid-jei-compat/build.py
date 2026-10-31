#!/usr/bin/env python3
"""Build a narrow, reproducible Maid Storage Manager / installed JEI hotfix."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import io
import json
import struct
import zipfile

TOOL = Path(__file__).resolve().parent
ROOT = TOOL.parents[1]
OUT = ROOT / 'releases/maid-jei-compat-20261027'
JAR = '1.20.1-maid_storage_manager-1.15.6.jar'
SOURCE = ROOT / 'releases/maid-addons-20261027/payload/mods' / JAR
SOURCE_SHA = 'fd72055823a296cba1a138f0940f3f44e35ecca7701c106c5f8403d16c105587'
CLASS = 'studio/fantasyit/maid_storage_manager/mixin/JEIRecipeTransferHook.class'
sha = lambda data: hashlib.sha256(data).hexdigest()


def update_annotation_offset(blob, pool, body):
    """Locate only the @Inject(method={"update"}) string index."""
    utf = lambda index: pool[index][1].decode()
    u2 = lambda offset: struct.unpack_from('>H', blob, offset)[0]
    hits = []

    def annotation(pos):
        kind = utf(u2(pos))
        count = u2(pos + 2)
        pos += 4
        for _ in range(count):
            key = utf(u2(pos))
            pos = value(pos + 2, kind == 'Lorg/spongepowered/asm/mixin/injection/Inject;' and key == 'method')
        return pos

    def value(pos, selected=False):
        tag = chr(blob[pos])
        pos += 1
        if tag in 'BCDFIJSZsc':
            if selected and tag == 's' and utf(u2(pos)) == 'update':
                hits.append(pos)
            return pos + 2
        if tag == 'e':
            return pos + 4
        if tag == '@':
            return annotation(pos)
        assert tag == '[', tag
        count = u2(pos)
        pos += 2
        for _ in range(count):
            pos = value(pos, selected)
        return pos

    pos = body + 6
    pos += 2 + 2 * u2(pos)
    for member_kind in ('field', 'method'):
        count = u2(pos)
        pos += 2
        for _ in range(count):
            name = utf(u2(pos + 2))
            attributes = u2(pos + 6)
            pos += 8
            for _ in range(attributes):
                attribute = utf(u2(pos))
                length = struct.unpack_from('>I', blob, pos + 2)[0]
                data = pos + 6
                if member_kind == 'method' and name == 'update' and attribute == 'RuntimeVisibleAnnotations':
                    cursor = data + 2
                    for _ in range(u2(data)):
                        cursor = annotation(cursor)
                    assert cursor == data + length
                pos = data + length
    assert len(hits) == 1, hits
    return hits[0]


def main():
    spec = importlib.util.spec_from_file_location('class_pool', ROOT / 'clients/cmi-expedition/tools/patch_mbtool_mouse_field.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = SOURCE.read_bytes()
    assert sha(original) == SOURCE_SHA, 'Unexpected upstream JAR'
    with zipfile.ZipFile(io.BytesIO(original)) as archive:
        infos = archive.infolist()
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert not any(n.upper().startswith('META-INF/') and n.upper().endswith(('.SF', '.RSA', '.DSA', '.EC')) for n in names)
        members = {name: archive.read(name) for name in names}
        comment = archive.comment
    before = members[CLASS]
    pool, body = module.pool(before)
    replacements = {b'onClose': b'onSuccessfulTransfer'}
    changes = []
    after = before
    edits = []
    for old, new in replacements.items():
        matches = [i for i, entry in pool.items() if entry[:2] == (1, old)]
        assert len(matches) == 1, (old, matches)
        index = matches[0]
        _, _, start, end = pool[index]
        edits.append((start, end, b'\x01' + struct.pack('>H', len(new)) + new))
        changes.append(dict(index=index, before=old.decode(), after=new.decode()))
    for start, end, replacement in sorted(edits, reverse=True):
        after = after[:start] + replacement + after[end:]
    after_pool, after_body = module.pool(after)
    assert [i for i in pool if pool[i][:2] != after_pool[i][:2]] == sorted(c['index'] for c in changes)
    assert before[body:] == after[after_body:]
    # The method name shares the original constant: append a selector constant.
    selector = b'update(Lnet/minecraft/world/inventory/AbstractContainerMenu;Lnet/minecraft/world/entity/player/Player;)V'
    selector_index = struct.unpack_from('>H', after, 8)[0]
    annotation_offset = update_annotation_offset(after, after_pool, after_body)
    new_body = bytearray(after[after_body:])
    struct.pack_into('>H', new_body, annotation_offset - after_body, selector_index)
    after = (after[:8] + struct.pack('>H', selector_index + 1) + after[10:after_body]
             + b'\x01' + struct.pack('>H', len(selector)) + selector + new_body)
    _, final_body = module.pool(after)
    expected_body = bytearray(before[body:])
    struct.pack_into('>H', expected_body, annotation_offset - after_body, selector_index)
    assert after[final_body:] == expected_body
    result = io.BytesIO()
    with zipfile.ZipFile(result, 'w') as archive:
        archive.comment = comment
        for info in infos:
            archive.writestr(copy.copy(info), after if info.filename == CLASS else members[info.filename])
    patched = result.getvalue()
    with zipfile.ZipFile(io.BytesIO(patched)) as archive:
        assert archive.testzip() is None
        assert archive.namelist() == names
        changed = [name for name in names if archive.read(name) != members[name]]
        assert changed == [CLASS]
    destination = OUT / 'payload/mods' / JAR
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(patched)
    evidence = OUT / 'evidence'
    evidence.mkdir(exist_ok=True)
    (evidence / 'original-hook.class').write_bytes(before)
    (evidence / 'patched-hook.class').write_bytes(after)
    report = dict(sourceJar=str(SOURCE), sourceJarSha256=SOURCE_SHA,
                  patchedJar=str(destination), patchedJarSha256=sha(patched),
                  changedZipMembers=changed, unchangedZipMembers=len(names)-1,
                  utf8Changes=changes, annotationSelector=selector.decode(),
                  annotationOnlyBodyChange=True, methodInstructionsUnchanged=True,
                  targetJei='15.59.0.212', deployed=False,
                  runtimeRestartRequired=True,
                  scope='JEI recipe transfer compatibility; all addon features and mixin registrations retained')
    (OUT / 'patch-manifest.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
