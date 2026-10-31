#!/usr/bin/env python3
"""Apply a reviewed payload revision while retaining installed predecessors."""
import hashlib, json, os, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
R=Path(__file__).resolve().parent
P=R.parents[1]
A=(Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,b):
    p.parent.mkdir(parents=True,exist_ok=True)
    fd,t=tempfile.mkstemp(prefix='.expedition-revision-',dir=p.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
        if p.exists():os.chmod(t,p.stat().st_mode&0o777)
        os.replace(t,p)
    finally:
        if os.path.exists(t):os.unlink(t)
def main():
    mp=R/'deployment-manifest.json';m=json.loads(mp.read_text());changes=[]
    for row in m['files']:
        b=(R/'payload'/row['path']).read_bytes();new=sha(b)
        if new==row['afterSha256']:continue
        targets=[('active-client',A/row['path'])]+[(root,P/root/row['path']) for root in ['servers/cmi-expedition/instance','servers/cmi-expedition/deployment','clients/cmi-expedition/overlay']]
        for root,p in targets:assert sha(p.read_bytes())==row['afterSha256'],str(p)
        changes.append((row,b,new,targets))
    assert changes,'No payload revisions'
    records=[]
    for row,b,new,targets in changes:
        old=row['afterSha256']
        for root,p in targets:
            backup=R/'backups/revisions'/old[:12]/root/row['path']
            if not backup.exists():write(backup,p.read_bytes())
            write(p,b);assert sha(p.read_bytes())==new
        row.setdefault('previousInstalledSha256',[]).append(old);row['afterSha256']=new
        for wr in m['workspaceFiles']:
            if wr['path']==row['path']:wr['afterSha256']=new
        records.append({'path':row['path'],'beforeSha256':old,'afterSha256':new})
    with zipfile.ZipFile(m['archive'],'w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted((R/'payload').rglob('*')):
            if p.is_file():z.writestr(str(p.relative_to(R/'payload')),p.read_bytes())
    m['archiveSha256']=sha(Path(m['archive']).read_bytes())
    m.setdefault('revisions',[]).append({'appliedAtUtc':datetime.now(timezone.utc).isoformat(),'files':records})
    write(mp,(json.dumps(m,ensure_ascii=False,indent=2)+'\n').encode())
    print(json.dumps({'revisedFiles':records,'archiveSha256':m['archiveSha256']},ensure_ascii=False))
if __name__=='__main__':main()
