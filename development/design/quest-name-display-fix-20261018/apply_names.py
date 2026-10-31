#!/usr/bin/env python3
"""Add missing quest main titles without changing subtitles or quest mechanics."""
import argparse
import copy
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FILES={'steam_railway.snbt','precision_component.snbt','ascend_on_burning_oil.snbt'}
ROOTS=[ROOT/p for p in ('clients/cmi-expedition/instance','clients/cmi-expedition/overlay','servers/cmi-expedition/instance')]
REL=Path('config/ftbquests/quests/chapters')
spec=importlib.util.spec_from_file_location('name_fix_surgery',ROOT/'design/researched-quest-integration-20261018/finish_existing_copy.py')
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)

def sha(blob):return hashlib.sha256(blob).hexdigest()
def encoded(data):return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode()
def atomic(path,blob):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name('.'+path.name+'.name-fix.tmp')
    try:
        with tmp.open('xb') as f:f.write(blob);f.flush();os.fsync(f.fileno())
        tmp.replace(path)
    finally:tmp.unlink(missing_ok=True)

def title(text,qid,value):
    a,b=s.quest_span(text,qid)
    block=text[a:b]
    # This pass adds only absent titles. An existing title is never rewritten.
    block=block[0]+'\n\t\t\ttitle: '+json.dumps(value,ensure_ascii=False)+block[1:]
    return text[:a]+block+text[b:]

def prepare():
    plan=json.loads((HERE/'naming-plan.json').read_text())
    byfile={name:{} for name in FILES}
    for row in plan['rows']:
        name=row['chapterFilename'];qid=row['questId'];label=row['proposedTitle']
        assert name in FILES and qid not in byfile[name]
        assert isinstance(label,str) and label.strip() and not re.fullmatch('[a-fA-F0-9]{8,}',label)
        assert not re.search(r'\b[a-z0-9_.-]+:[a-z0-9_./-]+\b',label),label
        byfile[name][qid]=label
    assert sum(map(len,byfile.values()))==105
    before,writes,rows={},{},[]
    for root in ROOTS:
        for name in sorted(FILES):
            path=root/REL/name
            raw=path.read_bytes();text=raw.decode();old=s.loads(text)
            qs={q['id']:q for q in old['quests']}
            missing={qid for qid,q in qs.items() if not q.get('title')}
            assert missing==set(byfile[name]),(name,missing^set(byfile[name]))
            for qid,label in byfile[name].items():
                assert not qs[qid].get('title')
                # Empty title fields are not present in these source files.
                a,b=s.quest_span(text,qid)
                assert 'title' not in qs[qid],(name,qid)
                text=title(text,qid,label)
                rows.append({'path':str(path.relative_to(ROOT)),'questId':qid,'title':label,'subtitle':qs[qid].get('subtitle')})
            new=s.loads(text)
            check=copy.deepcopy(new)
            for q in check['quests']:
                if q['id'] in byfile[name]:q.pop('title')
            assert check==old,'Non-title change: '+str(path)
            assert all(q.get('title') for q in new['quests'])
            before[path]=raw;writes[path]=text.encode()
            staged=HERE/'staging'/path.relative_to(ROOT)
            atomic(staged,writes[path])
    manifest_path=ROOT/'clients/cmi-expedition/evidence/overlay-files.json'
    manifest_raw=manifest_path.read_bytes();manifest=json.loads(manifest_raw)
    for path,blob in writes.items():
        if ROOTS[1] in path.parents:manifest[path.relative_to(ROOTS[1]).as_posix()]=sha(blob)
    before[manifest_path]=manifest_raw;writes[manifest_path]=encoded(manifest)
    return before,writes,rows

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    before,writes,rows=prepare()
    report={'applied':False,'mainTitles':105,'physicalTitleAdditions':len(rows),'subtitleAndDescriptionPreserved':True,
        'allNonTitleParsedFieldsUnchanged':True,'questTaskIdsAndDependenciesPreserved':True,
        'files':[{'path':str(p.relative_to(ROOT)),'beforeSha256':sha(before[p]),'afterSha256':sha(blob)} for p,blob in writes.items()],
        'titles':rows}
    if args.apply:
        backup=HERE/'backups'/datetime.now().strftime('%Y%m%d-%H%M%S')
        for p,blob in before.items():atomic(backup/p.relative_to(ROOT),blob)
        for p,blob in before.items():assert p.read_bytes()==blob,'Concurrent edit: '+str(p)
        done=[]
        try:
            for p,blob in writes.items():
                assert p.read_bytes()==before[p],'Concurrent edit: '+str(p)
                atomic(p,blob);done.append(p)
                assert p.read_bytes()==blob
        except BaseException:
            for p in reversed(done):atomic(p,before[p])
            raise
        report.update(applied=True,backupRoot=str(backup),appliedAt=datetime.now().astimezone().isoformat())
    atomic(HERE/('install-result.json' if args.apply else 'dry-run.json'),encoded(report))
    print(json.dumps({k:v for k,v in report.items() if k not in ('titles','files')},ensure_ascii=False))

if __name__=='__main__':main()
