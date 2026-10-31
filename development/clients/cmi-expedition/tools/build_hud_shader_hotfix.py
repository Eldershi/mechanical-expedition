"""Cumulative client patch for HUD defaults and the missing shader loader."""
from datetime import datetime
import hashlib
import json
import zipfile
from build_world_render_hotfix import FILES as PREVIOUS_FILES
from build_playtest_client import INSTANCE, OUT, VERSION, ROOT

FILES = PREVIOUS_FILES + [
    'config/xaerohud.txt', 'config/sodium-extra-options.json', 'config/oculus.properties',
    'config/iceandfire-client.toml',
    'mods/oculus-mc1.20.1-1.8.0.jar', 'mods/colorwheel-forge-1.3.0+mc1.20.1.jar',
] + sorted(p.relative_to(INSTANCE).as_posix() for p in (INSTANCE / 'shaderpacks').glob('*.zip'))

README = '''远征 0.2.0-test.1 · HUD 与光影累积修复

已安装测试 1：在下次正常结束游戏后，将本 ZIP 解压到含 mods、config、kubejs 的游戏目录，覆盖同名文件，再正常启动。
不要把本补丁作为新整合包导入。无需重复下载全量客户端或叠加旧补丁。
本补丁不覆盖 options.txt，保留按键等个人设置；首次应用会设置下列 HUD 默认值。

小地图默认移到右上角，左上角显示简洁 FPS。
关闭冰火传说的自定义主菜单接管，恢复原有 FancyMenu 主菜单、背景和标题图。
恢复 Oculus 1.8.0 与 Colorwheel 1.3.0，补上光影加载器和机械动力兼容组件。
下次启动后入口：选项 → 视频设置 → 光影包。
保留 Photon v1.3b、BSL 10.1.8 与 BSL 的 Colorwheel 补丁版，默认关闭光影。
这些是客户端模组，不需要服务器更新。PC 显卡实际效果尚待玩家验证。

包含开局与世界/渲染配置：普通视距 12，DH 64，取消高度距离裁剪；
恢复原 HUD、怪奇宝典原图，开局教程去重、七咒之戒自动装备及联机成就音效修复。
群系与结构间距由世界生成配置控制，详见世界与渲染配置说明。
客户端脚本每次加载仅应用一次默认值，之后可以正常手动调整。

不含存档、账号、Minecraft、Java；不修改服务器或玩家背包。
'''

def main():
    name = f'机械动力-远征-{VERSION}-HUD与光影修复补丁.zip'
    target = OUT / name
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in FILES:
            archive.write(INSTANCE / relative, relative)
        archive.writestr('HUD与光影修复说明.txt', README.encode('utf-8-sig'))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert 'options.txt' not in archive.namelist()
        for relative in FILES:
            assert archive.read(relative) == (INSTANCE / relative).read_bytes()
    digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    sums = OUT / 'SHA256SUMS.txt'
    lines = [line for line in sums.read_text().splitlines() if not line.endswith('  ' + name)]
    sums.write_text('\n'.join(lines + [digest + '  ' + name]) + '\n')
    (OUT / 'HUD与光影修复说明.txt').write_text(README, encoding='utf-8-sig')
    report = {'at': datetime.now().astimezone().isoformat(), 'file': str(target),
              'bytes': target.stat().st_size, 'sha256': digest, 'files': FILES,
              'preservesExistingKeybindings': True, 'effectiveOnNextNormalLaunch': True,
              'nativeGraphicsTested': False}
    (ROOT / 'evidence/hud-shaders/client-hotfix.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'files'}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
