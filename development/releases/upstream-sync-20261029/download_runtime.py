#!/usr/bin/env python3
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,tomllib,subprocess
R=Path(__file__).resolve().parent; U=R/'upstream'; D=R/'downloads/runtime'
D.mkdir(parents=True,exist_ok=True)
inventory=json.loads((R.parent.parent/'evidence/upstream-review-20261029/file-inventory.json').read_text())
tsv={}
for line in (U/'updater/update.tsv').read_text().splitlines():
    fields=line.split('\t')
    if len(fields)>=3: tsv[fields[1]]={'sha1':fields[0],'url':fields[2]}
rows=[]
for x in inventory:
    if not x['path'].startswith('mods/.index/') or x['status']=='removed': continue
    stem=Path(x['path']).name.removesuffix('.pw.toml'); data=tomllib.loads((U/x['path']).read_text())
    if stem in {'alltheleaks','pipez-optimizer'}:
        rows.append({'name':data['name'],'filename':data['filename'],'status':'keep_intentionally_absent'});continue
    dl=data['download']; file=data['filename']; link=dl.get('url') or tsv['mods/'+file]['url']
    rows.append({'name':data['name'],'filename':file,'url':link,'hashAlgorithm':dl['hash-format'],'expectedHash':dl['hash'],'status':'pending'})
def fetch(row):
    if row['status']!='pending':return row
    p=D/row['filename']
    if not p.exists():
        subprocess.run(['curl','--fail','--location','--retry','2','--max-time','90','--silent','--show-error','--output',str(p),row['url']],check=True)
    b=p.read_bytes(); actual=hashlib.new(row['hashAlgorithm'],b).hexdigest()
    if actual!=row['expectedHash']:raise ValueError('Checksum mismatch: '+str(p))
    row.update({'status':'downloaded_verified','bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()});return row
with ThreadPoolExecutor(max_workers=4) as pool:
    for item in pool.map(fetch,rows):print(item['status'],item['filename'],flush=True)
(R/'evidence/runtime-downloads.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
