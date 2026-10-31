"""Build an HMCL-compatible mrpack using hash-matched Modrinth CDN files only.

All other files, including local compatibility patches, stay in overrides.
The full import ZIP is the source of truth; filenames never select a download.
"""
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit, urlunsplit, quote, unquote
from datetime import datetime
import argparse, hashlib, json, ssl, urllib.request, zipfile
from build_playtest_client import ROOT, OUT, VERSION
from mod_removal_policy import load_removal_policy, jar_mod_ids, validate_mod_rows

LIGHT_NAME = f'机械动力-远征-{VERSION}-HMCL轻量包.mrpack'

def normalize(url):
    p = urlsplit(url)
    assert p.scheme == 'https' and p.netloc == 'cdn.modrinth.com'
    return urlunsplit((p.scheme, p.netloc, quote(unquote(p.path), safe='/:@+'), p.query, ''))

def resolve(hashes):
    request = urllib.request.Request('https://api.modrinth.com/v2/version_files',
        data=json.dumps({'hashes': hashes, 'algorithm': 'sha1'}).encode(),
        headers={'User-Agent': 'Expedition-Pack-Builder/1.0', 'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(request, timeout=45,
            context=ssl.create_default_context(cafile='/etc/ssl/cert.pem')) as response:
        return json.load(response)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--metadata', type=Path, help='Previously retrieved official hash lookup response')
    args = parser.parse_args()
    full = OUT / f'机械动力-远征-{VERSION}-Windows客户端.zip'
    removal_policy = load_removal_policy(ROOT)
    files = {}
    mod_rows = []
    with zipfile.ZipFile(full) as z:
        for entry in z.infolist():
            if entry.filename.startswith('overrides/mods/') and entry.filename.endswith('.jar'):
                blob = z.read(entry)
                mod_rows.append({'file': PurePosixPath(entry.filename).name, 'modIds': jar_mod_ids(blob)})
                files[entry.filename.removeprefix('overrides/')] = {
                    'sha1': hashlib.sha1(blob).hexdigest(), 'sha512': hashlib.sha512(blob).hexdigest(),
                    'sha256': hashlib.sha256(blob).hexdigest(), 'size': len(blob)}
    removal_review = validate_mod_rows(mod_rows, removal_policy, client=True)
    assert len(files) == removal_policy['expectedClientModCount'], ('Review changed client mod count', len(files))
    evidence = ROOT / 'evidence/light-import-hmcl-20261017'
    evidence.mkdir(exist_ok=True)
    metadata = json.loads(args.metadata.read_text()) if args.metadata else resolve([r['sha1'] for r in files.values()])
    if not args.metadata:
        (evidence / 'modrinth-hash-resolve.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    downloads, bundled = [], []
    for path, hashes in sorted(files.items()):
        version = metadata.get(hashes['sha1'], {})
        matches = [f for f in version.get('files', []) if
                   f.get('hashes', {}).get('sha1') == hashes['sha1'] and
                   f.get('hashes', {}).get('sha512') == hashes['sha512'] and
                   f.get('size') == hashes['size'] and
                   urlsplit(f.get('url', '')).netloc == 'cdn.modrinth.com']
        if matches:
            urls = list(dict.fromkeys(normalize(f['url']) for f in matches))
            downloads.append({'path': path, 'hashes': {k: hashes[k] for k in ('sha1', 'sha512')},
                              'downloads': urls, 'fileSize': hashes['size'],
                              'env': {'client': 'required', 'server': 'unsupported'}})
        else:
            bundled.append({'file': PurePosixPath(path).name, 'sha256': hashes['sha256'], 'bytes': hashes['size']})
    target = OUT / LIGHT_NAME
    temp = target.with_name(target.name + '.building')
    index = {'formatVersion': 1, 'game': 'minecraft', 'versionId': VERSION,
             'name': '机械动力：远征 '+VERSION, 'summary': '文礼、玩家互伤关闭、满饱食进食、双手饰品栏、铁路与下界及烟花苦力怕修复。',
             'files': downloads, 'dependencies': {'minecraft': '1.20.1', 'forge': '47.4.10'}}
    downloaded = {row['path'] for row in downloads}
    instructions = f'''机械动力：远征 · HMCL 轻量包

将“{LIGHT_NAME}”拖入 HMCL 主窗口，选择“安装整合包”，不要先解压。
建议将新实例命名为 expedition_test3；使用 64 位 Java 17。
游戏版本为 Minecraft 1.20.1 / Forge 47.4.10。
24/32GB 及以上电脑建议分配 12GB，16GB 电脑先分配 8GB。

本包内置专用补丁和非 Modrinth 来源文件；HMCL 会联网下载其余 {len(downloads)} 个模组（约 {sum(f['fileSize'] for f in downloads) / 1e9:.2f} GB），以及 Minecraft、Forge 和启动库。
全部模组与完整客户端内容一致，无需叠加其他补丁。
包含山地地形、雪线林线、建筑地形筛选，以及科技和冒险任务书。
包含文礼；关闭玩家互伤，允许满饱食进食，提供两个手部饰品栏，并包含下界呼吸与苦力怕变体烟花兼容。
核能苦力怕保持原生行为；幻影苦力怕及分身会转换烟花。
铁路结构避让由随包兼容组件处理；已有受损结构不自动重建。
请新建实例导入；包中不包含旧世界或地图缓存，沿用旧实例会继续显示其本地保存的旧地图。
进入多人游戏，选择预置服务器 mc6.r9mc.cn:47054。
公共模组和玩法脚本需要服务端采用兼容版本；生成客户端安装包不执行线上部署。
光影默认关闭；需要时在“选项 → 视频设置 → 光影包”选择 BSL 或 Photon。

请建立独立实例，避免混入不完整的导入文件。
若依然提示下载失败，请在 HMCL 的下载/日志详情里查找具体失败文件和网址；该提示本身不包含失败项。
'''
    with zipfile.ZipFile(full) as old, zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as out:
        out.writestr('modrinth.index.json', json.dumps(index, ensure_ascii=False, indent=2) + '\n')
        for entry in old.infolist():
            if not entry.filename.startswith('overrides/'): continue
            relative = entry.filename.removeprefix('overrides/')
            if relative in downloaded: continue
            blob = instructions.encode('utf-8-sig') if relative == '安装说明-Windows.txt' else old.read(entry)
            out.writestr(entry.filename, blob)
        out.writestr('安装说明.txt', instructions.encode('utf-8-sig'))
    with zipfile.ZipFile(temp) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        overrides = [n for n in z.namelist() if n.startswith('overrides/mods/') and n.endswith('.jar')]
        assert len(downloads) + len(overrides) == len(files)
        assert not downloaded.intersection(n.removeprefix('overrides/') for n in overrides)
        for row in bundled:
            assert hashlib.sha256(z.read('overrides/mods/' + row['file'])).hexdigest() == row['sha256']
        for name in z.namelist():
            p = PurePosixPath(name)
            assert not p.is_absolute() and '..' not in p.parts and '\\' not in name
    temp.replace(target)
    (OUT / '安装说明-HMCL轻量包.txt').write_text(instructions, encoding='utf-8-sig')
    report = {'builtAt': datetime.now().astimezone().isoformat(), 'version': VERSION,
              'importRevision': index['versionId'], 'file': str(target), 'bytes': target.stat().st_size,
              'sha256': hashlib.file_digest(target.open('rb'), 'sha256').hexdigest(),
              'downloadedModCount': len(downloads), 'bundledModCount': len(bundled), 'totalModCount': len(files),
              'downloadBytes': sum(row['fileSize'] for row in downloads), 'bundled': bundled,
              'downloadDomains': ['cdn.modrinth.com'], 'sourceFullPackage': str(full),
              'metadataContentHashesVerified': True, 'archiveIntegrityPassed': True,
              'windowsNativeLaunchTested': False,
              'removalPolicySha256': removal_review['removalPolicySha256']}
    (OUT / 'light-client-build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    (evidence / 'build-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'bundled'}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
