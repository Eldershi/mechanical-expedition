#!/usr/bin/env python3
from pathlib import Path
from zipfile import ZipFile
import hashlib,json,shutil,tomllib
R=Path(__file__).resolve().parent; S=R/'staging/mods'
def ids(path):
    try:
        with ZipFile(path) as z: data=tomllib.loads(z.read('META-INF/mods.toml').decode())
        return {x['modId'] for x in data.get('mods',[])}
    except (KeyError,ValueError,tomllib.TOMLDecodeError): return set()
rows=json.loads((R/'evidence/runtime-downloads.json').read_text())
# BCLib is deliberately pinned by the existing validated worldgen patch.
# See evidence/bclib-compat-review/decision.json before changing this exception.
sources=[R/'downloads/runtime'/x['filename'] for x in rows if x['status']=='downloaded_verified' and x['name']!='BCLib']
sources += [R/'upstream/mods/CMI Core-1.3-1.20.1-all.jar',R/'upstream/mods/Steam-Letters-2.0.0-1.20.1.jar']
backup=R/'evidence/replaced-staging-mods'; backup.mkdir(exist_ok=True)
installed=[]; removed=[]
for source in sources:
    module_ids=ids(source)
    if not module_ids: raise RuntimeError('No Forge mod IDs: '+str(source))
    replacements=[p for p in S.glob('*.jar') if ids(p)&module_ids and p.name!=source.name]
    if (S/source.name).exists(): replacements.append(S/source.name)
    for old in replacements:
        raw=old.read_bytes()
        record={'filename':old.name,'sha256':hashlib.sha256(raw).hexdigest(),'modIds':sorted(ids(old))}
        shutil.copy2(old,backup/old.name); old.unlink(); removed.append(record)
    target=S/source.name
    shutil.copy2(source,target)
    installed.append({'filename':source.name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'modIds':sorted(module_ids)})
out={'installed':installed,'removedFromStagingOnly':removed,'preservedLegacySteam':['Create-Steam-Ages-1.0.jar','steampowered-1.20.1-3.1.0.jar'],'preservedAbsent':['AllTheLeaks','PipezOptimizer'],'coreFilenameIsNotVersionProof':True}
(R/'evidence/runtime-mod-changes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'installed':len(installed),'replacedOldFiles':len(removed),'ids':[x['modIds'] for x in installed]},ensure_ascii=False,indent=2))
