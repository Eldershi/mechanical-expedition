#!/usr/bin/env python3
"""Split the existing adventure chapters into the user-requested groups."""
from pathlib import Path
from datetime import datetime
import fcntl
import hashlib
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
ROOTS = [ROOT / p for p in (
    'clients/cmi-expedition/instance',
    'clients/cmi-expedition/overlay',
    'servers/cmi-expedition/instance',
)]
REL = Path('config/ftbquests/quests')
OLD = '54D4CAA40ADB5408'
MAGIC = hashlib.sha256(b'cmi-expedition:chapter-group:magic').hexdigest()[:16].upper()
DIMENSIONS = {
    'bumblezone_01_exploration.snbt',
    'research_adventure_a_alex.snbt',
    'research_adventure_a_twilight.snbt',
    'research_adventure_a_starlight.snbt',
    'research_adventure_a_aether.snbt',
    'research_adventure_a_undergarden.snbt',
    'research_adventure_a_deeper.snbt',
}
spec = importlib.util.spec_from_file_location('quest_import', ROOT / 'tools/quest-workbench/import_bumblezone.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
loads = module.parser()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def atomic(path, blob):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name('.' + path.name + '.adventure-groups.tmp')
    try:
        tmp.write_bytes(blob)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def main():
    manifest = ROOT / 'clients/cmi-expedition/evidence/overlay-files.json'
    lock = manifest.parent / '.overlay-files.lock'
    with lock.open('a+b') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        before, writes, titles = {}, {}, {}
        for base in ROOTS:
            chapter_root = base / REL / 'chapters'
            chapters = sorted([*chapter_root.glob('research_adventure_*.snbt'), chapter_root / 'bumblezone_01_exploration.snbt'])
            assert len(chapters) == 16
            for path in chapters:
                blob = path.read_bytes()
                doc = loads(blob.decode())
                assert doc['group'] == OLD, ('unexpected source group', path)
                titles[path.name] = doc['title']
                if path.name in DIMENSIONS:
                    continue
                text, count = re.subn(r'(?m)^\tgroup: "' + OLD + '"$', '\tgroup: "' + MAGIC + '"', blob.decode())
                assert count == 1
                updated = loads(text)
                assert updated == dict(doc, group=MAGIC)
                before[path], writes[path] = blob, text.encode()
            path = base / REL / 'chapter_groups.snbt'
            blob = path.read_bytes()
            doc = loads(blob.decode())
            groups = doc['chapter_groups']
            assert not any(g['id'] == MAGIC or g.get('title') == '魔法' for g in groups)
            source = [g for g in groups if g['id'] == OLD]
            assert len(source) == 1 and source[0]['title'] == '异境冒险'
            text, count = re.subn(r'(id: "' + OLD + r'"\s+title: )"异境冒险"', r'\1"秘境冒险"', blob.decode())
            assert count == 1
            end = text.rfind('\t]')
            assert end > 0
            text = text[:end] + '\t\t{\n\t\t\tid: "' + MAGIC + '"\n\t\t\ttitle: "魔法"\n\t\t}\n' + text[end:]
            updated = loads(text)
            expected = [dict(g, title='秘境冒险') if g['id'] == OLD else g for g in groups]
            assert updated == dict(doc, chapter_groups=expected + [{'id': MAGIC, 'title': '魔法'}])
            before[path], writes[path] = blob, text.encode()
        assert len(writes) == 30
        # Read and merge the shared manifest only while holding its existing lock.
        before[manifest] = manifest.read_bytes()
        previous = json.loads(before[manifest])
        merged = dict(previous)
        for path, blob in writes.items():
            if ROOTS[1] in path.parents:
                merged[path.relative_to(ROOTS[1]).as_posix()] = sha(blob)
        writes[manifest] = encoded(merged)
        backup = OUT / 'backups' / datetime.now().strftime('%Y%m%d-%H%M%S')
        for path, blob in before.items():
            assert path.read_bytes() == blob, ('concurrent edit', path)
            atomic(backup / path.relative_to(ROOT), blob)
        completed = []
        try:
            for path, blob in writes.items():
                assert path.read_bytes() == before[path], ('concurrent edit', path)
                atomic(path, blob)
                completed.append(path)
                assert path.read_bytes() == blob
        except BaseException:
            for path in reversed(completed):
                assert path.read_bytes() == writes[path], ('concurrent edit during rollback', path)
                atomic(path, before[path])
            raise
        for name in titles:
            blobs = [(base / REL / 'chapters' / name).read_bytes() for base in ROOTS]
            assert len(set(blobs)) == 1, ('three-root mismatch', name)
        for base in ROOTS:
            docs = [loads((base / REL / 'chapters' / name).read_text()) for name in titles]
            assert sum(d['group'] == OLD for d in docs) == 7
            assert sum(d['group'] == MAGIC for d in docs) == 9
        touched_keys = {p.relative_to(ROOTS[1]).as_posix() for p in writes if ROOTS[1] in p.parents}
        assert all(merged[k] == v for k, v in previous.items() if k not in touched_keys)
        report = {
            'applied': True,
            'dimensionChapters': [titles[n] for n in titles if n in DIMENSIONS],
            'magicChapters': [titles[n] for n in titles if n not in DIMENSIONS],
            'allChapterFieldsExceptGroupPreserved': True,
            'threeRootsIdentical': True,
            'unrelatedManifestEntriesPreserved': True,
            'backupRoot': str(backup),
            'files': [{'path': str(p.relative_to(ROOT)), 'beforeSha256': sha(before[p]), 'afterSha256': sha(b)} for p, b in writes.items()],
        }
        atomic(OUT / 'install-result.json', encoded(report))
        print(json.dumps({k: v for k, v in report.items() if k != 'files'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
