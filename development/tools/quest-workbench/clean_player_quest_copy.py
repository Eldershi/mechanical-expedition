#!/usr/bin/env python3
"""Apply reviewed, exact player-copy edits without changing quest mechanics."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EVIDENCE = HERE/'evidence/bumblezone-line-fix-20261018'
spec = importlib.util.spec_from_file_location('copy_snbt', ROOT/'clients/cmi-expedition/tools/ftb_snbt.py')
parser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parser)

def sha(blob):
    return hashlib.sha256(blob).hexdigest()

def atomic(path, blob):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp = path.with_name('.'+path.name+'.copy-cleanup.tmp')
    try:
        tmp.write_bytes(blob)
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)

def without_player_copy(doc):
    result = deepcopy(doc)
    for quest in result.get('quests', []):
        for field in ('title','subtitle','description'):
            quest.pop(field, None)
    return result

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--apply',action='store_true')
    args = ap.parse_args()
    audit = json.loads((EVIDENCE/'player-copy-audit.json').read_text())
    proposals = {}
    for finding in audit['findings']:
        # The Bumblezone repair has already rewritten its complete player prose
        # while retaining the runtime identities, which differ from old copies.
        if finding['fileName'].startswith('bumblezone'):
            continue
        for affected in finding['affectedFiles']:
            path = Path(affected['path'])
            assert ROOT in path.parents and path.suffix == '.snbt' and not path.is_symlink()
            proposals.setdefault(path, []).append(finding)
    before, writes, edits = {}, {}, []
    for path, findings in proposals.items():
        raw = path.read_bytes()
        doc = parser.loads(raw.decode())
        updated = deepcopy(doc)
        by_id = {q['id']:q for q in updated.get('quests', [])}
        changes = {}
        for f in findings:
            quest = by_id.get(f['questId'])
            if not quest:
                continue
            field, old, new = f['field'], f['originalParagraph'], f['suggestedParagraph']
            assert field in ('title','subtitle','description')
            values = quest.get(field, [])
            if isinstance(values,list) and old in values:
                quest[field] = [new if value == old else value for value in values
                                if not (value == old and new is None)]
            elif values == old:
                quest[field] = new or ''
            else:
                continue
            if old in changes:
                assert changes[old] == new
            changes[old] = new
            edits.append({'path':str(path.relative_to(ROOT)), 'questId':f['questId'],
                          'findingId':f['findingId'], 'old':old, 'new':new})
        text = raw.decode()
        for old,new in changes.items():
            token = json.dumps(old,ensure_ascii=False)
            assert token in text, 'Unexpected SNBT string encoding: '+str(path)
            # Preserve the original byte format and every non-text SNBT literal.
            text = text.replace(token, json.dumps(new or '',ensure_ascii=False))
        parsed = parser.loads(text)
        # Empty paragraphs are harmless and retain exact SNBT delimiters; the
        # renderer skips them. All detectors, identities, rewards and links stay.
        assert without_player_copy(parsed) == without_player_copy(doc), str(path)
        if text.encode() != raw:
            before[path], writes[path] = raw, text.encode()
    manifest_path = ROOT/'clients/cmi-expedition/evidence/overlay-files.json'
    manifest_raw = manifest_path.read_bytes()
    manifest = json.loads(manifest_raw)
    overlay = ROOT/'clients/cmi-expedition/overlay'
    for path,blob in list(writes.items()):
        if overlay in path.parents:
            manifest[path.relative_to(overlay).as_posix()] = sha(blob)
    if writes:
        before[manifest_path] = manifest_raw
        writes[manifest_path] = (json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode()
    result = {'at':datetime.now().astimezone().isoformat(),'applied':False,
              'changedChapterFiles':len(writes)-(1 if writes else 0),
              'changedQuestParagraphs':len(edits),'mechanicsUnchanged':True,
              'playerDataWritten':False, 'changes':edits,
              'files':[{'path':str(p.relative_to(ROOT)),'beforeSHA256':sha(before[p]),
                        'afterSHA256':sha(blob)} for p,blob in writes.items()]}
    if args.apply and writes:
        backup = EVIDENCE/('copy-backup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        for path,raw in before.items():
            atomic(backup/path.relative_to(ROOT),raw)
        done=[]
        try:
            for path,blob in writes.items():
                assert path.read_bytes() == before[path], 'Concurrent edit: '+str(path)
                atomic(path,blob); done.append(path)
                assert path.read_bytes() == blob
        except BaseException:
            for path in reversed(done): atomic(path,before[path])
            raise
        result.update(applied=True,backup=str(backup))
    EVIDENCE.mkdir(parents=True,exist_ok=True)
    atomic(EVIDENCE/'player-copy-cleanup-result.json', (json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({k:v for k,v in result.items() if k not in ('changes','files')},ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
