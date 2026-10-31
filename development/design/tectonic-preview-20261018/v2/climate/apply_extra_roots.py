"""Apply only the seven additional alpine roots; does not alter the installed JAR."""
from pathlib import Path
import importlib.util
import json

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('installer',HERE/'install_climate.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
instance=installer.EXPECTED
if not (instance/'.alpine-climate-installed.json').exists():raise SystemExit('Install main climate bundle first')
if list((instance/'saves').glob('*/level.dat')):raise SystemExit('A save exists: apply these resources only after exiting and before creating a new world')
changes=[]
for path in sorted((HERE/'additional-placement-overrides').rglob('*.json')):
    target=instance/'kubejs/data'/path.relative_to(HERE/'additional-placement-overrides')
    if instance not in target.resolve().parents:raise SystemExit('Escaping v2 target')
    data=path.read_bytes()
    if target.exists() and target.read_bytes()==data:continue
    if target.exists():installer.write(instance/'.alpine-climate-backups/additional-seven'/target.relative_to(instance),target.read_bytes())
    installer.write(target,data);changes.append(str(target.relative_to(instance)))
installer.write(instance/'.alpine-climate-extra-roots.json',(json.dumps({'applied_files':changes,'jar_changed':False,'existing_271_roots_changed':False},ensure_ascii=False,indent=2)+'\n').encode())
print(json.dumps({'extra_roots_written':len(changes),'jar_changed':False,'restart_if_world_datapacks_already_loaded':True},ensure_ascii=False))
