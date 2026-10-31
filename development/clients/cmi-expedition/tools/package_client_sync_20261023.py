"""Package the prior player patch plus reviewed later client changes, without personal data."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,zipfile,tomllib

ROOT=Path(__file__).resolve().parents[3]
INSTANCE=ROOT/'clients/cmi-expedition/instance'
OUT=ROOT/'releases/client-sync-20261023'
OLD=ROOT/'releases/0.2.0-test.3/机械动力-远征-0.2.0-test.3-玩法修复共用补丁.zip'
LATER=[
 'kubejs/server_scripts/expedition/DisableBlockingLaboratoryMap.js',
 'kubejs/server_scripts/expedition/RestoreBrassMixing.js',
 'kubejs/assets/create_jetpack/models/item/jetpack_placeable.json',
 'kubejs/assets/create_jetpack/models/item/netherite_jetpack_placeable.json',
 'kubejs/config/expedition-selected-native-recipes.json',
 'kubejs/server_scripts/expedition/SelectedParallelRecipes.js',
 'kubejs/startup_scripts/expedition/RecipeRouteLabels.js',
 'kubejs/config/expedition-recipe-labels.json',
]
def sha(blob):return hashlib.sha256(blob).hexdigest()
def encode(obj):return (json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode()
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 baselines={f'0.2.0-test.{v}':{row['path']:row for row in json.loads((ROOT/f'releases/0.2.0-test.{v}/client-files.json').read_text())} for v in (2,3)}
 with zipfile.ZipFile(OLD) as z:
  old_rows=json.loads(z.read('gameplay-fix-files.json'))
  old_hashes={row['path']:row['sha256'] for row in old_rows}
  for row in old_rows:
   name=row['path'];current=(INSTANCE/name).read_bytes()
   if name.endswith('.toml'):assert tomllib.loads(current.decode())==tomllib.loads(z.read(name).decode('utf-8-sig'))
   else:assert sha(current)==row['sha256'],name
  payload={row['path']:(INSTANCE/row['path']).read_bytes() for row in old_rows}
 payload.update({name:(INSTANCE/name).read_bytes() for name in LATER})
 assert len(payload)==17
 application=json.loads((ROOT/'clients/cmi-expedition/evidence/recipe-parallel-20261022/application.json').read_text())
 assert application['remoteStatus']=='deployed_and_reload_verified'
 regression=json.loads((ROOT/'clients/cmi-expedition/evidence/gameplay-batch-20261019/test-server/kubejs/exported/gameplay-batch-regression.json').read_text())
 assert regression['passed']
 for name,want in application['files'].items():assert sha(payload[name])==want
 icons=json.loads((ROOT/'clients/cmi-expedition/evidence/jetpack-icons-20261021/validation.json').read_text());assert icons['status']=='fixed'
 files=[]
 for name,blob in payload.items():
  prior={version:rows[name]['sha256'] if name in rows else None for version,rows in baselines.items()}
  if name in old_hashes:prior['priorGameplayPatch']=old_hashes[name]
  files.append({'path':name,'archivePath':'payload/'+name,'bytes':len(blob),'sha256':sha(blob),'previousSha256':prior,'group':'prior-test2-to-test3' if name not in LATER else 'later-reviewed-changes','installAction':'skip_if_target_hash_matches_otherwise_backup_and_replace'})
 manifest={'patchId':'expedition-client-sync-20261023','createdAt':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'baseVersions':list(baselines),'target':'0.2.0-test.3 + reviewed client changes through 2026-10-22','minecraft':'1.20.1','forge':'47.4.10','java':'17, 64-bit','files':files,'fileCount':len(files),'priorPatchFileCount':9,'laterFileCount':8,'deleteFiles':[],
  'scope':['Shared gameplay compatibility components','Selected native recipes kept alongside current CMI recipes','One-line JEI recipe route labels','Placeable jetpack item models','Native heated brass mixing','Blocking laboratory-map lookup mitigation for local worlds'],
  'preserve':['saves','options.txt','optionsof.txt','servers.dat','screenshots','accounts and launcher metadata','Xaero minimap/world map/waypoints','resourcepacks and shader selection','FTB player/team progress'],
  'excluded':['server-only teleport fix JAR','idle pregeneration scripts','server.properties','local caches and exports','personal keybind migration receipts','mod updater .index metadata','unfinished quest drafts','arcane-industry prototype'],
  'validation':{'archiveAndPayloadHashesVerified':True,'newCombinedClientLaunchTested':False,'priorGameplayCombinedRuntimePassed':True,'recipeColdAndReloadPassed':True,'onlineRecipeReloadPassed':True,'jetpackNativeAndJeiRenderPassed':True,'jeiRouteLabelVisualVerified':False}}
 mods={version:[row for name,row in rows.items() if name.startswith('mods/') and name.endswith('.jar')] for version,rows in baselines.items()}
 notes='''机械动力：远征 · 客户端累计同步补丁 · 2026-10-23

适用于原 test.2 或 test.3，Minecraft 1.20.1 / Forge 47.4.10 / 64 位 Java 17。
这是局部累计包，不能作为完整整合包导入。旧版或身份不明实例需要另行核对。

共 17 个游戏文件，具体路径及哈希见 sync-manifest.json。
先将 ZIP 解压到临时目录，读取 sync-manifest.json，再把 payload/ 内文件逐一安装到实际游戏根目录。
不要把 payload 文件夹整体套进实例；不要清空 mods/config/kubejs。
已是目标 SHA256 的文件跳过。覆盖前备份每个相关旧文件；不自动删除任何文件。
遇到未知本地修改，不猜测覆盖；报告具体文件与差异。目标是保留两套配方并行。

包含：三枚公共模组、持续进食、双手饰品栏、玩家伤害与下界呼吸处理、烟花苦力怕、配方并行及简短标记、黄铜原配方、两个可放置喷气背包图标，以及实验室地图搜索保护。
实验室保护脚本只在本地世界执行，联机时由服务器自己的脚本执行；客户端存有 server_scripts 不等于服务端专用模组。

客户端更新后必须完整重启，单独 F3+T 无法加载 startup_scripts。
JEI 悬停产物标记：◆ 魔改配方；新增恢复路线 ◇ 原配方。标记实际画面尚未核验。
配方原生目录中高级注液器、烈焰人燃烧室、抽屉模板三项无独立可恢复制作配方，保留现状。

连接地址：优先尝试 cn1.i9idc.com:12375，另一入口 mc6.r9mc.cn:47054。
连接可用性需在玩家网络中核验。
不覆盖服务器列表，不携带账号、令牌、地图、存档、截图或玩家数据。
回退：只恢复安装备份中的文件，并移出安装前不存在的新增文件；不回滚世界或玩家进度。

打包检查覆盖 ZIP 完整性与全部17个文件的SHA256；客户端启动、配方画面及联机状态需在目标实例核验。
'''
 provenance={'sourceArchive':{'path':str(OLD.relative_to(ROOT)),'sha256':sha(OLD.read_bytes())},'sourceFiles':LATER,'excludedDifferences':{'config/packetfixer.properties':'timestamp comment only','config/zfastnoise.mixin.properties':'timestamp comment only','config/oculus.properties':'timestamp comment only','config/leawind_third_person.json':'personal camera preference','config/jei/ingredient-list-mod-sort-order.ini':'generated local ordering','config/jei/world/':'personal lookup history'},'modDeltaSinceFullTest3':[],'unfinishedQuestDraftsIncluded':False,'productionInstanceModifiedByPackaging':False}
 package=OUT/'机械动力-远征-客户端累计同步补丁-20261023.zip'
 with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for name,blob in payload.items():z.writestr('payload/'+name,blob)
  z.writestr('sync-manifest.json',encode(manifest));z.writestr('baseline-mods.json',encode(mods));z.writestr('安装说明.txt',notes);z.writestr('来源与变更.json',encode(provenance))
 with zipfile.ZipFile(package) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  for name in z.namelist():assert not name.startswith('/') and '..' not in Path(name).parts
  for row in files:assert sha(z.read(row['archivePath']))==row['sha256']
 package_hash=sha(package.read_bytes())


 (OUT/'安装说明.txt').write_text(notes)
 (OUT/'sync-manifest.json').write_bytes(encode(manifest))
 (OUT/'来源与变更.json').write_bytes(encode(provenance))
 (OUT/'SHA256SUMS.txt').write_text(package_hash+'  '+package.name+'\n')
 report={'package':str(package.relative_to(ROOT)),'bytes':package.stat().st_size,'sha256':package_hash,'fileCount':len(files),'priorFiles':9,'laterFiles':8,'archiveIntegrityPassed':True,'allHashesVerified':True,'wholeClientLaunchTestedThisRun':False,'productionFilesModified':False}
 (OUT/'build-report.json').write_bytes(encode(report));print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
