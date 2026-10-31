"""Cumulative small client update; never replace existing keybindings/options."""
from pathlib import Path
from datetime import datetime
import hashlib, json, zipfile
from build_onboarding_hotfix import FILES as ONBOARDING_FILES
from build_playtest_client import INSTANCE, OUT, VERSION, PROJECT

FILES = ONBOARDING_FILES + [
    'config/tectonic.json', 'config/sparsestructures.json5',
    'config/terrablender.toml', 'config/expedition-boss-density.json', 'config/cso-common.toml',
    'config/betterfpsdist.json', 'config/DistantHorizons.toml',
    'kubejs/data/minecraft/worldgen/structure_set/strongholds.json',
    'kubejs/client_scripts/event/ExpeditionRenderDefaults.js',
]
README = '''远征 0.2.0-test.1 · 世界与渲染配置补丁

已安装测试 1：把本 ZIP 解压到含 mods、config、kubejs 的游戏目录，覆盖同名文件。
无需重新下载全量客户端；不要把补丁作为新整合包导入。
本补丁不会覆盖 options.txt，因此保留按键等个人设置。

新启动的客户端自动设置普通视距 12 区块，遥远地平线保留 64 区块。
取消 Better FPS 按高度计算的距离裁剪，取消 DH 高度雾。
上述设置在客户端启动时应用。
普通设置后续可以手动更改，不会每帧强制锁定。

群系尺度、结构间距、要塞环距及暮色首领地标密度由随包配置控制。
TerraBlender 使用整数区域缩放级别；自然群系形状不按固定倍数复制。
普通结构保留单体建筑大小。客户端补丁不执行服务器世界重建。

包含开局配置：HUD、怪奇宝典原图、成就音效、自动戒指与统一教程。
本补丁不含存档、账号、游戏本体、Java 或新增模组。
'''

def main():
    name = f'机械动力-远征-{VERSION}-世界与渲染修复补丁.zip'
    target = OUT / name
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in FILES:
            archive.write(INSTANCE / relative, relative)
        archive.writestr('世界与渲染修复说明.txt', README.encode('utf-8-sig'))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert 'options.txt' not in archive.namelist()
        assert not any(n.startswith(('saves/', 'logs/', 'mods/')) for n in archive.namelist())
    digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    sums = OUT / 'SHA256SUMS.txt'
    lines = [line for line in sums.read_text().splitlines() if not line.endswith('  ' + name)]
    sums.write_text('\n'.join(lines + [digest + '  ' + name]) + '\n')
    (OUT / '世界与渲染修复说明.txt').write_text(README, encoding='utf-8-sig')
    report = {'at': datetime.now().astimezone().isoformat(), 'file': name,
              'bytes': target.stat().st_size, 'sha256': digest, 'files': FILES,
              'preservesExistingKeybindings': True, 'effectiveOnNextNormalLaunch': True}
    evidence = PROJECT / 'servers/cmi-expedition/evidence/scale5-reset'
    (evidence / 'client-hotfix.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
