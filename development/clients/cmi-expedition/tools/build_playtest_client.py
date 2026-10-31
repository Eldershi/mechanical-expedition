"""Package the current tested client as a self-contained CurseForge-format import ZIP."""
from pathlib import Path,PurePosixPath
from datetime import datetime
import hashlib,json,struct,zipfile
from mod_removal_policy import load_removal_policy, validate_client_mods

ROOT=Path(__file__).resolve().parents[1]
INSTANCE=ROOT/'instance'
PROJECT=ROOT.parents[1]
VERSION='0.2.0-test.3'
OUT=PROJECT/'releases'/VERSION
FOLDERS=['mods','config','shaderpacks','defaultconfigs','hotai','ldlib','patchouli_books','moonlight-global-datapacks',
         'datapacks','tlm_custom_pack','resourcepacks','oeb','oei','oef']
SKIP={'config/resourceful-config-web.json','config/touhou_little_maid/sites',
      'config/roadweaver/structure_cache_overworld.json',
      'config/chunky/tasks','config/fancymenu/last_world.meta',
      'config/expedition-keybind-migrations.json',
      'kubejs/client_scripts/event/ExpeditionSessionPerformance.js'}
FORBIDDEN_PARTS={'.git','.index','.cache','__pycache__','saves','logs','crash-reports','screenshots',
                 'backups','exported','probe','.expedition','updater'}
def allowed(relative):
    path=PurePosixPath(relative)
    if relative.startswith('config/spark/') and relative!='config/spark/config.json': return False
    if path.suffix in ('.jfr','.sparkprofile','.log'): return False
    return not(set(path.parts)&FORBIDDEN_PARTS) and path.name!='.DS_Store' and not any(relative==s or relative.startswith(s+'/') for s in SKIP)
def digest(blob):return hashlib.sha256(blob).hexdigest()
def servers_dat():
    def string(value):
        blob=value.encode('utf-8');return struct.pack('>H',len(blob))+blob
    def entry(name,value):return b'\x08'+string(name)+string(value)
    server=entry('name','机械动力：远征 '+VERSION)+entry('ip','mc6.r9mc.cn:47054')+b'\x00'
    return b'\x0a\x00\x00\x09'+string('servers')+b'\x0a'+struct.pack('>i',1)+server+b'\x00'
def performance_note():
    report=json.loads((ROOT/'evidence/performance-community-20261017/final-performance-report.json').read_text())
    phases=report['phases']
    still=[p['fpsMeanAll'] for p in phases if p['phase'].startswith('static')]
    moving=[p['fpsMeanAll'] for p in phases if not p['phase'].startswith('static')]
    return (f"性能报告中的静止平均 {min(still):.0f}–{max(still):.0f} FPS，"
            f"移动平均 {min(moving):.0f}–{max(moving):.0f} FPS。统计配置与逐帧耗时见性能诊断与实测.txt；实际帧率需在目标电脑核验。")

def build():
    removal_policy=load_removal_policy(ROOT)
    OUT.mkdir(parents=True,exist_ok=True)
    package=OUT/f'机械动力-远征-{VERSION}-Windows客户端.zip'
    temporary=package.with_name(package.name+'.building')
    files={}
    for folder in FOLDERS:
        source=INSTANCE/folder
        if not source.exists():continue
        for p in source.rglob('*'):
            relative=p.relative_to(INSTANCE).as_posix()
            if p.is_file() and not p.is_symlink() and allowed(relative):files[relative]=p
    for folder in ['startup_scripts','server_scripts','client_scripts','data','assets','config']:
        for p in (INSTANCE/'kubejs'/folder).rglob('*'):
            relative=p.relative_to(INSTANCE).as_posix()
            if p.is_file() and not p.is_symlink() and allowed(relative):files[relative]=p
    for name in ['LICENSE','License.md','icon.png','SOURCE.json','kubejs/guide-tome-catalog.json']:
        p=INSTANCE/name
        if p.is_file():files[name]=p
    mods=sorted(p for p in files if p.startswith('mods/') and p.endswith('.jar'))
    removal_review=validate_client_mods([files[name] for name in mods],removal_policy)
    expected_mod_count=removal_policy['expectedClientModCount']
    assert len(mods)==expected_mod_count,('Review changed client mod count',len(mods))
    assert not any(any(x in n for x in ('expedition-recipe-audit','-prototype-','expedition-ui-probe')) for n in mods)
    manifest={'minecraft':{'version':'1.20.1','modLoaders':[{'id':'forge-47.4.10','primary':True}]},
        'manifestType':'minecraftModpack','manifestVersion':1,'name':'机械动力：远征',
        'version':VERSION,'author':'Expedition local playtest','files':[],'overrides':'overrides'}
    readme=f'''机械动力：远征 {VERSION} · Windows 联机测试客户端

安装：
1. 将整个 ZIP 作为整合包导入支持 CurseForge 格式的启动器（不要先解压）。
2. 启动器应识别 Minecraft 1.20.1、Forge 47.4.10；选择 64 位 Java 17。
3. 24/32GB 及以上系统可分配 12GB，16GB 系统先用 8GB，保留系统所需内存。通用导入格式不会自动修改启动器的 JVM 参数。
4. 首次启动联网安装 Minecraft 和 Forge。模组已随包提供。
5. 多人游戏里选择预置的“机械动力：远征 {VERSION}”。地址：mc6.r9mc.cn:47054。
   公共模组和玩法脚本需要服务端采用兼容版本；生成客户端安装包不执行线上部署。

此包包含 {len(mods)} 个客户端模组，包括法术／机械／Quark 思索和 JEMM。
一级为各流派专属卷轴，二级为具体法术；进入菜单后可按 Backspace 返回上级。
遥远的地平线 LOD 渲染半径为 64 区块，普通视距为 12，模拟距离为 5。
地形配置包含山地高差调整、雪线和林线，以及普通陆地建筑的地形选址筛选；世界高度范围为 -64 至 383。
包含科技与冒险任务书；“秘境冒险”和“魔法”使用独立分组，蜜蜂领域使用统一任务章节。
不包含旧世界、Xaero 地图/路标缓存、Distant Horizons 数据库或旧道路结构缓存。请作为新实例导入，避免旧实例残留地图。
已移除 TES 头顶血条与伤害飘字；恢复 Xaero 原生小地图外框。
烟花苦力怕每次引爆都会触发，覆盖已装的苦力怕变体（核能除外）；不破坏地形、不伤害生物，击杀烟花保持关闭。
加入文礼 Civillis；建筑提供文明值，降低基地周围的自然刷怪。
关闭玩家相互伤害；满饱食度也能继续吃食物；手部饰品栏由 1 个增至 2 个。
移除整合包核心的下界缺氧规则，保留正常水下与太空呼吸机制。
通达铁路结构避让由随包兼容组件处理；已有受损结构不自动重建。
禁止蛆和苍蝇自然生成，关闭僵尸死亡出蛆。
修复强制英文物品名的配置，并补充 47 条已核对的中文；完整汉化仍在逐项完善。
关闭 FastNoise 的噪声写入加速路径，保留群系加速。
小地图默认在右上角，左上角显示简洁 FPS；下次启动后应用。
模组选择由随包 mod-removal-20261018.json 控制；保留矿藏开采及 FancyMenu 主菜单背景和标题图。
已恢复 Oculus 光影加载器与 Colorwheel 机械动力兼容组件。
已附 Photon v1.3b 与 BSL 10.1.8；选项 → 视频设置 → 光影包，默认关闭。
已修复配方树每 tick 重建全部配方的开销，并减少密集叶丛的内部叶面渲染（保留两层外叶）；保留界面原生分辨率，3D 固定缩放并保护 1920×1080 下限。
普通视距 12、DH 64，保留远景原有细节、透明度、抗锯齿及环境遮蔽。
3D 固定渲染比例 0.53；在 1440p/1080p 显示器会自动提高比例保护 FHD 下限，不使用动态分辨率或插帧。
已修正 DH 等待更新时的空转分配，关闭 spark 常驻原生采样；按需诊断使用 Java 采样。
已修复进服物品扫描与配方同步并发调用超级刀时的 Rhino 崩溃；保留原物品 ID、属性与无限耐久。
{performance_note()}
光影与 DH 的实际画面仍待对应 PC 显卡验证。
开局配置使用资源包 HUD 和怪奇宝典原图，统一开局教程并自动装备七咒之戒；成就弹窗使用原版提示音。
Photon 作者不支持 Apple GPU；此包的光影选择面向 Windows PC。请使用独立实例导入本测试版。
测试问题反馈请附游戏 logs/latest.log 与 crash-reports 中对应报告。
本版本按固定整包分发，后续通过新测试包更新。

底座：革新构件 Beta 2.5.0；保留原 LICENSE、License.md 与 SOURCE.json。
客户端启动、首次导入及图形效果需在目标平台核验。
'''
    generated={
        'mod-removal-20261018.json':(ROOT/'mod-removal-20261018.json').read_bytes(),
        'servers.dat':servers_dat(),
        'options.txt':b'lang:zh_cn\nrenderDistance:12\nsimulationDistance:5\nguiScale:3\nmaxFps:260\nenableVsync:false\nautoJump:false\nfullscreen:false\nkey_key.ftbchunks.map:key.keyboard.unknown\nkey_gui.xaero_open_map:key.keyboard.m\nkey_iris.keybind.reload:key.keyboard.f9\n',
        'pack-info.json':(json.dumps({'name':'机械动力：远征','version':VERSION,'minecraft':'1.20.1',
            'forge':'47.4.10','java':17,'recommendedHeapMiB':12288,'fallbackHeapMiB':16384,'minimumWorldResolution':[1920,1080],'worldRenderScale':0.53,'dynamicResolution':False,'frameGeneration':False,'server':'mc6.r9mc.cn:47054','modCount':len(mods),
            'vanillaRenderChunks':12,'dhLodChunks':64,
            'releaseRevision':'20261019-gameplay-civillis','terrainProfile':'tectonic-mountain-coordination-v2',
            'worldMinY':-64,'worldHeight':448,'oldMapCachesIncluded':False,
            'verticalDistanceCulling':False,'minimapCorner':'TOP_RIGHT','fpsCorner':'TOP_LEFT','showFps':True,
            'shaderLoader':'Oculus 1.8.0','createShaderCompatibility':'Colorwheel 1.3.0',
            'shaders':['Photon v1.3b','BSL 10.1.8'],'shadersEnabledByDefault':False},ensure_ascii=False,indent=2)+'\n').encode(),
        '性能诊断与实测.txt':(ROOT/'evidence/performance-community-20261017/性能诊断与实测.txt').read_bytes(),
        '安装说明-Windows.txt':readme.encode('utf-8-sig')
    }
    rows=[]
    with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        for relative,path in sorted(files.items()):
            blob=path.read_bytes()
            assert len(blob) == path.stat().st_size, ('Incomplete source read', relative)
            if relative == 'config/oculus.properties':
                blob=blob.decode().replace('enableShaders=true','enableShaders=false').encode()
            z.writestr('overrides/'+relative,blob)
            rows.append({'path':relative,'sha256':digest(blob),'bytes':len(blob)})
        for relative,blob in generated.items():
            z.writestr('overrides/'+relative,blob);rows.append({'path':relative,'sha256':digest(blob),'bytes':len(blob)})
        z.writestr('安装说明-Windows.txt',readme.encode('utf-8-sig'))
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        names=z.namelist();assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts for n in names)
        assert len([n for n in names if n.startswith('overrides/mods/') and n.endswith('.jar')])==expected_mod_count
        assert not any(set(PurePosixPath(n).parts)&FORBIDDEN_PARTS for n in names)
        for row in rows:assert digest(z.read('overrides/'+row['path']))==row['sha256']
    temporary.replace(package)
    (OUT/'安装说明-Windows.txt').write_bytes(readme.encode('utf-8-sig'))
    package_hash=hashlib.file_digest(package.open('rb'),'sha256').hexdigest()
    (OUT/'SHA256SUMS.txt').write_text(package_hash+'  '+package.name+'\n')
    (OUT/'client-files.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    report={'builtAt':datetime.now().astimezone().isoformat(),'version':VERSION,'file':str(package),
        'bytes':package.stat().st_size,'sha256':package_hash,'modCount':len(mods),'fileCount':len(rows),
        'archiveIntegrityPassed':True,'fileHashesVerified':True,'windowsNativeLaunchTested':False,
        'format':'CurseForge manifest v1; all mod JARs bundled in overrides; launcher installs Minecraft/Forge',
        'sourceInstance':str(INSTANCE),'removalPolicySha256':removal_review['removalPolicySha256']}
    (OUT/'client-build.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':build()
