"""Build cumulative client fixes with a fixed FHD render-scale floor."""
from datetime import datetime
import hashlib,json,zipfile
from build_hud_shader_hotfix import FILES as PREVIOUS_FILES
from build_playtest_client import INSTANCE,OUT,ROOT,VERSION,performance_note
FILES=list(dict.fromkeys(PREVIOUS_FILES+[
 'mods/CullLessLeaves-Reforged-1.20.1-1.0.5.jar',
 'mods/expedition-client-performance-1.0.0.jar',
 'mods/renderscale-1.4.0-alpha.6-forge+1.20.1.jar','config/renderscale.json5',
 'config/cull-less-leaves.json','config/spark/config.json',
 'kubejs/startup_scripts/register/item/equipment/Tools.js','SOURCE.json']))
batch = ROOT/'evidence/playtest-batch-20261017'
FILES = list(dict.fromkeys(FILES + json.loads((batch/'merged-candidates.json').read_text())['files']
 + json.loads((batch/'client-world-scale.json').read_text())['files']
 + ['config/zfastnoise.mixin.properties',
    'shaderpacks/BSL_v10.1.8.zip.txt','shaderpacks/BSL_v10.1.8 + Clrwl_1.0.5.zip.txt']))
README="""远征 0.2.0-test.1 · 客户端性能累积修复

已有客户端：正常结束游戏后，解压本补丁到含 mods、config、kubejs 的游戏目录，覆盖同名文件，下次启动生效。
运行同目录的“移除旧TES.cmd”，或手动删除 mods/tslatentitystatus-forge-1.20.1-1.6.6.jar。
烟花苦力怕需要客户端与服务端采用兼容的模组和配置。
不要作为新整合包导入；无需叠加旧补丁。不覆盖 options.txt 或个人按键。

修复 JECT 每个客户端 tick 重建全量配方集合的开销，保留配方树和全部配方。
新增 CullLessLeaves，减少密集叶丛内部叶面渲染，保留两层外叶；叶丛通透度可能有轻微差别。
修复默认视距脚本的数字转换异常；普通视距 12、DH 64、取消高度裁剪。
采用固定 3D 缩放，界面保持原生清晰度；3D 下限保护为 1920×1080。
保留 DH 原有细节、透明度、抗锯齿与环境遮蔽；不用动态分辨率或插帧。
修正 DH 队列在等待更新时反复创建临时对象的问题，保留所有更新。
正常游玩不启用自动 JFR 采样，本包不包含本地诊断脚本。
关闭 spark 常驻原生后台采样；保留按需诊断，使用 /sparkc profiler start --force-java-sampler。
修复进服物品扫描与配方同步并发调用超级刀时的 Rhino 崩溃；保留原物品 ID、属性与无限耐久。
移除 TES，恢复 Xaero 原生外框；烟花苦力怕沿用 3% 触发率。
群系及结构间距由随包配置控制；补丁不删除个人存档。
禁止蛆、苍蝇自然生成与僵尸死亡出蛆，保留刷怪蛋和人工召唤。
修复强制英文物品名的配置，并补充 47 条已核对的中文。
关闭 FastNoise 噪声写入加速，保留群系加速。
BSL 使用自身日月渲染并关闭镜头光斑。

@@PERFORMANCE@@
性能统计见随包报告；光影默认关闭，实际运行效果需在目标电脑核验。

包含原 HUD、怪奇宝典原图、开局教程去重、七咒之戒自动装备、主菜单及光影入口修复。
不含存档、账号、测试探针。无需服务器安装新增的客户端模组。
GUI 材质包请独立从官方获取 create:mcGUI 2.1.0，本补丁不再直接打包 ARR 资源包。
官方页面：https://www.curseforge.com/minecraft/texture-packs/create-mcgui/files/9176699
更新文件后需在 Paxi 加载顺序及 options.txt 原位置将 create_mcGUI_2.0.1.zip 替换为 create_mcGUI_2.1.0.zip。
"""
def main():
 note=README.replace('@@PERFORMANCE@@',performance_note())
 name=f'机械动力-远征-{VERSION}-客户端性能累积补丁.zip'
 target=OUT/name
 temporary=target.with_name(target.name+'.building')
 with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for relative in FILES:z.write(INSTANCE/relative,relative)
  z.writestr('客户端性能修复说明.txt',note.encode('utf-8-sig'))
  z.writestr('移除旧TES.cmd', '@echo off\r\nsetlocal\r\ndel /q "%~dp0mods\\tslatentitystatus-forge-1.20.1-1.6.6.jar" 2>nul\r\nif exist "%~dp0mods\\tslatentitystatus-forge-1.20.1-1.6.6.jar" (echo TES removal failed. Close Minecraft and retry. & pause & exit /b 1)\r\necho TES removed. Start the updated client normally.\r\npause\r\n')
  z.write(ROOT/'evidence/performance-community-20261017/性能诊断与实测.txt','性能诊断与实测.txt')
 with zipfile.ZipFile(temporary) as z:
  assert z.testzip() is None
  assert 'options.txt' not in z.namelist()
  assert all(z.read(relative)==(INSTANCE/relative).read_bytes() for relative in FILES)
 temporary.replace(target)
 sha=hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
 report={'at':datetime.now().astimezone().isoformat(),'file':str(target),'sha256':sha,'bytes':target.stat().st_size,'files':FILES,'effectiveOnNextNormalLaunch':True,'nativeCounterTargetsMet':json.loads((ROOT/'evidence/performance-community-20261017/final-performance-report.json').read_text())['counterTargetsMet'],'smoothnessGuaranteed':False,'fixedResolutionScaling':0.53,'minimumWorldResolution':[1920,1080],'dynamicResolution':False,'frameGeneration':False,'serverChangeRequired':True,'removedMods':['tslatentitystatus-forge-1.20.1-1.6.6.jar']}
 (OUT/'客户端性能修复说明.txt').write_text(note,encoding='utf-8-sig')
 (ROOT/'evidence/performance-community-20261017/client-hotfix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
