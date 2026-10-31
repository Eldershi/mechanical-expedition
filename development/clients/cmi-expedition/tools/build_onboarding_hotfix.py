"""Package the small onboarding fix for already imported test clients."""
from pathlib import Path
from datetime import datetime
import hashlib, json, zipfile
from build_playtest_client import ROOT, INSTANCE, OUT, VERSION

FILES = [
    'config/asteorbar-client.toml', 'config/achievement_toast-client.toml',
    'config/enigmaticlegacy-common.omniconf', 'config/ars_nouveau-common.toml',
    'config/tconstruct-common.toml', 'config/botania-common.toml',
    'config/touhou_little_maid-common.toml',
    'config/paxi/resourcepacks/Eternal-Snowstorm-s-MC-i18n-Chinese-pack.zip',
    'kubejs/server_scripts/expedition/GuideTome.js',
]
README = '''远征 0.2.0-test.1 · 10 月 17 日开局修复补丁

已导入旧测试 1 客户端：把此 ZIP 解压到实例的游戏目录，覆盖同名文件。
游戏目录是包含 mods、config、kubejs 的目录，不要把它作为一个新整合包导入。
未安装客户端：直接导入更新后的完整 .mrpack 或 Windows 客户端 ZIP，无需再安装本补丁。

修复内容：恢复资源包 HUD；怪奇宝典恢复模组原图；成就弹窗保留并改用原版音效；七咒之戒自动装备；开局教程由完整怪奇宝典统一提供。
重复开局书仅合并一次，匹配物品及完整 NBT，保留改名或带自定义数据的书。没有完整宝典时不会清理。

本机运行中的客户端可按 F3+T 刷新资源包图标，客户端 HUD 和提示音配置由 Forge 热重载。
服务端部分通过脚本热加载应用，在线玩家无需重新进服；合并开局书约需 10 秒。
本补丁不包含存档、账号、Java、Minecraft 或额外模组。
'''

def main():
    name = f'机械动力-远征-{VERSION}-开局修复补丁.zip'
    target = OUT / name
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative in FILES:
            archive.write(INSTANCE / relative, relative)
        archive.writestr('修复补丁说明.txt', README.encode('utf-8-sig'))
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert not any(n.startswith(('saves/', 'logs/', 'mods/')) for n in archive.namelist())
    digest = hashlib.file_digest(target.open('rb'), 'sha256').hexdigest()
    sums = OUT / 'SHA256SUMS.txt'
    lines = [line for line in sums.read_text().splitlines() if not line.endswith('  ' + name)]
    sums.write_text('\n'.join(lines + [digest + '  ' + name]) + '\n')
    (OUT / '修复补丁说明.txt').write_text(README, encoding='utf-8-sig')
    record = {'at': datetime.now().astimezone().isoformat(), 'file': name,
              'bytes': target.stat().st_size, 'sha256': digest, 'files': FILES,
              'application': 'Server hot reload; client Forge config reload and F3+T for resources.'}
    (ROOT / 'evidence/onboarding-fixes/client-hotfix.json').write_text(
        json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(record, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
