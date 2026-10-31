#!/usr/bin/env python3
"""Apply the reviewed payload with checksums and per-file backups."""
import argparse, hashlib, json, os, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path
R = Path(__file__).resolve().parent
P = R.parents[1]
A = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')
ROOTS = ['servers/cmi-expedition/instance', 'servers/cmi-expedition/deployment', 'clients/cmi-expedition/overlay']
def read(p): return p.read_bytes() if p.exists() else None
def sha(b): return hashlib.sha256(b).hexdigest() if b is not None else None
def atomic(p, b):
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix='.expedition-material-', dir=p.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(b); f.flush(); os.fsync(f.fileno())
        if p.exists(): os.chmod(temp, p.stat().st_mode & 0o777)
        os.replace(temp, p)
    finally:
        if os.path.exists(temp): os.unlink(temp)
def save(p, j): atomic(p, (json.dumps(j, ensure_ascii=False, indent=2)+'\n').encode())
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--active', action='store_true'); args=ap.parse_args()
    mp=R/'deployment-manifest.json'
    if args.active:
        m=json.loads(mp.read_text())
        for row in m['files']:
            assert sha(read(A/row['path'])) in (row['beforeSha256'],row['afterSha256']), row['path']
            assert sha((R/'payload'/row['path']).read_bytes())==row['afterSha256']
        for row in m['files']:
            p=A/row['path']; old=read(p); backup=R/'backups/active-client-before'/row['path']
            if old is not None and not backup.exists() and sha(old)==row['beforeSha256']: atomic(backup,old)
            atomic(p,(R/'payload'/row['path']).read_bytes())
            assert sha(p.read_bytes())==row['afterSha256']
        m['activeClientStatus']='installed_and_hash_verified'; m['activeClientInstalledAtUtc']=datetime.now(timezone.utc).isoformat(); save(mp,m)
        print(json.dumps({'activeClient':str(A),'installedFiles':len(m['files']),'verified':True},ensure_ascii=False)); return
    assert not mp.exists(), 'Preparation already completed; preserve original backups'
    payloads=[(p.relative_to(R/'payload'),p.read_bytes()) for p in sorted((R/'payload').rglob('*')) if p.is_file()]
    assert payloads, 'Empty payload'
    rows=[]; workspace=[]
    for rel,b in payloads:
        assert '..' not in rel.parts and not rel.is_absolute()
        if rel.suffix=='.json': json.loads(b)
        rows.append({'path':str(rel),'beforeSha256':sha(read(A/rel)),'afterSha256':sha(b)})
        for root in ROOTS:
            p=P/root/rel; old=read(p); backup=R/'backups/project-before'/root/rel
            if old is not None:
                assert not backup.exists(); atomic(backup,old)
            workspace.append({'root':root,'path':str(rel),'beforeSha256':sha(old),'afterSha256':sha(b)})
    for rel,b in payloads:
        for root in ROOTS:
            atomic(P/root/rel,b); assert sha((P/root/rel).read_bytes())==sha(b)
    archive=R/'expedition-material-unification-native-processing-20261028.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,b in payloads: z.writestr(str(rel),b)
    m={'preparedAtUtc':datetime.now(timezone.utc).isoformat(),'activeClient':str(A),'activeClientStatus':'pending','onlineStatus':'pending','files':rows,'workspaceFiles':workspace,'archive':str(archive),'archiveSha256':sha(archive.read_bytes())}
    save(mp,m); print(json.dumps({'files':len(rows),'archive':str(archive),'manifest':str(mp)},ensure_ascii=False))
if __name__=='__main__': main()
