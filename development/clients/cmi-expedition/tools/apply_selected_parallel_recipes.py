"""Apply the tested, additive recipe patch and package exactly those four files."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,shutil,zipfile

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=ROOT/'clients/cmi-expedition/evidence/recipe-parallel-20261022'
BACKUP=ROOT/'backups/recipe-parallel-20261022'
FIXTURE=EVIDENCE/'runtime2'
DESTINATIONS=['clients/cmi-expedition/instance','clients/cmi-expedition/overlay',
    'servers/cmi-expedition/instance','servers/cmi-expedition/deployment']
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
    audit=json.loads((FIXTURE/'kubejs/exported/expedition-selected-parallel-audit.json').read_text())
    milestones=json.loads((FIXTURE/'kubejs/exported/expedition-cmi-smoke.json').read_text())
    previous=json.loads((FIXTURE/'kubejs/exported/expedition-pre-steam-audit.json').read_text())
    assert audit['passed'] and milestones['passed'] and previous['passed']
    assert audit['retainedCount'] > 39000, 'Must include added CMI recipes, not only originalRecipes'
    assert json.loads((EVIDENCE/'reload-audit.json').read_text())['passed']
    cold=(EVIDENCE/'runtime-final-cold-console.log').read_text(errors='replace')
    assert 'Done (' in cold and '[Selected Parallel] passed=true' in cold
    assert (EVIDENCE/'SelectedParallelRecipes.js').read_bytes()==(FIXTURE/'kubejs/server_scripts/expedition/SelectedParallelRecipes.js').read_bytes()
    for name in ['expedition-selected-parallel-audit.json','expedition-cmi-smoke.json','expedition-pre-steam-audit.json']:
        shutil.copy2(FIXTURE/'kubejs/exported'/name,EVIDENCE/('cold-'+name))
    cold_labels=json.loads((FIXTURE/'kubejs/exported/expedition-recipe-labels.json').read_text())
    reload_labels=json.loads((EVIDENCE/'recipe-labels.json').read_text())
    labels={key:sorted(set(cold_labels[key])|set(reload_labels[key])) for key in ['modified','native']}
    label_bytes=(json.dumps(labels,ensure_ascii=False,indent=2)+'\n').encode()
    files={
        'kubejs/config/expedition-selected-native-recipes.json':(EVIDENCE/'catalog.json').read_bytes(),
        'kubejs/server_scripts/expedition/SelectedParallelRecipes.js':(EVIDENCE/'SelectedParallelRecipes.js').read_bytes(),
        'kubejs/startup_scripts/expedition/RecipeRouteLabels.js':(EVIDENCE/'RecipeRouteLabels.js').read_bytes(),
        'kubejs/config/expedition-recipe-labels.json':label_bytes,
    }
    assert json.loads((EVIDENCE/'label-unit-tests.json').read_text())['passed']
    hashes={name:sha(blob) for name,blob in files.items()}
    receipt=EVIDENCE/'application.json'
    prior=json.loads(receipt.read_text()).get('prior',{}) if receipt.exists() else {}
    for parent in DESTINATIONS:
        for relative,blob in files.items():
            target=ROOT/parent/relative
            if target.exists():
                prior.setdefault(str(target.relative_to(ROOT)),sha(target.read_bytes()))
                backup=BACKUP/target.relative_to(ROOT)
                if prior[str(target.relative_to(ROOT))] is not None and not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
            else:prior[str(target.relative_to(ROOT))]=None
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(blob)
    manifest=ROOT/'clients/cmi-expedition/evidence/overlay-files.json'
    backup=BACKUP/manifest.relative_to(ROOT)
    if not backup.exists():backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(manifest,backup)
    data=json.loads(manifest.read_text());data.update(hashes)
    manifest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    for parent in DESTINATIONS:
        assert all(sha((ROOT/parent/name).read_bytes())==hashes[name] for name in files)
    out=ROOT/'releases/0.2.0-test.3/recipe-parallel-20261022';out.mkdir(parents=True,exist_ok=True)
    note='''原配方与魔改配方并行补丁 · 2026-10-22
按 Space 清单勾选的 239 项开放原模组配方，保留现有配方、物品及任务。
客户端和服务端均覆盖 kubejs 目录；重启客户端以加载 JEI 配方标记，服务端可 /reload。
在 JEI 中悬停配方产物：◆ 魔改配方；恢复的原配方显示 ◇ 原配方。无需新模组。
修复配方解析线程与 CMI JavaScript 回调的兼容问题，不改变机器运行速度。
高级注液器是 CMI 自创；烈焰人燃烧室原版通过捕捉获得；抽屉模板在原模组无独立配方。
这三项保留现状，其他所选内容恢复有原生对应的可用路线。
验证：独立测试服冷启动、重载、原配方与当前配方保留、15 个后期里程碑、6 类前期构件。
JEI 标记通过逻辑分支测试；完整生存通关与标记实际画面未验证。
线上服同步状态见 Space 清单处理回执；本包不含世界、账号或玩家数据。
回退：移除本补丁新增的四个文件；若此前存在同名文件，使用对应备份恢复。
'''
    patch=out/'机械动力-远征-原配方并行与简短标记-20261022.zip'
    with zipfile.ZipFile(patch,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for relative,blob in files.items():z.writestr(relative,blob)
        z.writestr('补丁说明.txt',note)
    with zipfile.ZipFile(patch) as z:
        assert z.testzip() is None and all(z.read(name)==blob for name,blob in files.items())
    (out/'SHA256SUMS.txt').write_text(sha(patch.read_bytes())+'  '+patch.name+'\n')
    application={'recordedAt':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'selectionPage':json.loads((EVIDENCE/'selection.json').read_text())['url'],
        'selectedItems':239,'status':'applied_locally_and_packaged','remoteStatus':'pending_chrome_deployment',
        'files':hashes,'destinations':DESTINATIONS,'prior':prior,'patch':str(patch.relative_to(ROOT)),
        'patchSha256':sha(patch.read_bytes()),'coldAudit':audit,'milestones':milestones,'existingNativeAudit':previous,
        'labels':{key:len(value) for key,value in labels.items()},'visualLabelVerified':False}
    (EVIDENCE/'application.json').write_text(json.dumps(application,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':application['status'],'patch':str(patch),'bytes':patch.stat().st_size,
        'selectedItems':239,'coldCounts':audit['counts'],'labels':application['labels']},ensure_ascii=False))
if __name__=='__main__':main()
