"""Validate preservation and syntax before any live installation."""
from pathlib import Path
import hashlib, json, subprocess, shutil, tomllib, zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
STAGE = ROOT/'staging'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    before = json.loads((ROOT/'evidence/active-before.json').read_text())['files']
    failures, changed, protected = [], [], []
    catalogs = ['kubejs/config/expedition-selected-native-recipes.json',
        'kubejs/config/expedition-pre-steam-recipes.json','kubejs/config/expedition-material-unification.json']
    for rel in catalogs:
        ok = (STAGE/rel).is_file() and digest(STAGE/rel) == before[rel]['sha256']
        protected.append({'path':rel,'preserved':ok})
        if not ok: failures.append({'kind':'restored_catalog_changed','path':rel})
    for rel, row in before.items():
        path = STAGE/rel
        after = digest(path) if path.is_file() else None
        if after == row['sha256']:
            continue
        changed.append({'path':rel,'beforeSha256':row['sha256'],'afterSha256':after})
        if rel.startswith(('kubejs/server_scripts/expedition/','kubejs/startup_scripts/expedition/','kubejs/client_scripts/expedition/','updater/')):
            failures.append({'kind':'protected_expedition_file_changed','path':rel})
    node = shutil.which('node')
    checked_js, checked_json = 0, 0
    for p in STAGE.rglob('*'):
        if not p.is_file() or p.is_symlink(): continue
        rel = p.relative_to(STAGE).as_posix()
        if rel.startswith(('kubejs/exported/','kubejs/probe/','config/jei/')): continue
        old = before.get(rel)
        if old and digest(p) == old['sha256']: continue
        if p.suffix == '.js' and rel.startswith('kubejs/') and node:
            r = subprocess.run([node,'--check',str(p)],capture_output=True,text=True)
            checked_js += 1
            if r.returncode: failures.append({'kind':'javascript_syntax','path':rel,'error':r.stderr[:1800]})
        if p.suffix == '.json' and rel.startswith('kubejs/'):
            try:
                json.loads(p.read_text())
                checked_json += 1
            except Exception as e: failures.append({'kind':'json_syntax','path':rel,'error':str(e)})
    ids = {}
    for jar in (STAGE/'mods').glob('*.jar'):
        with zipfile.ZipFile(jar) as z:
            if 'META-INF/mods.toml' not in z.namelist(): continue
            metadata = tomllib.loads(z.read('META-INF/mods.toml').decode())
            for mod in metadata.get('mods',[]): ids.setdefault(mod['modId'],[]).append(jar.name)
    for mod, names in ids.items():
        if len(names)>1: failures.append({'kind':'duplicate_mod_id','modId':mod,'files':names})
    report = {'passed':not failures,'protectedCatalogs':protected,'changedExistingCount':len(changed),
        'changedExisting':changed,'checkedJavaScript':checked_js,'checkedJson':checked_json,
        'modIds':len(ids),'failures':failures,'productionTouched':False}
    (ROOT/'evidence/static-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['passed','changedExistingCount','checkedJavaScript','checkedJson','modIds','failures']},ensure_ascii=False))
    raise SystemExit(0 if report['passed'] else 1)

if __name__ == '__main__': main()
