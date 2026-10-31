"""Package the reviewed grass, natural-weather and shader-key fixes locally.

Default: show the plan. --patch creates only the new small patch, notes, payload
snapshot and checksum entries. --apply additionally rewrites the four existing
local distributions, after the caller has completed runtime verification.
No remote upload, desktop delivery or source-instance edits are performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import shutil
import tempfile
from zoneinfo import ZoneInfo
import zipfile

from package_curios_unification import (
    ROOT, CLIENT, SERVER, OUT, FULL, LIGHT, CUMULATIVE, SERVER_ZIP,
    SERVER_METADATA, sha, blob_sha, json_bytes, read_json, manifest_rows,
    cow_copy, rewrite_archive, inspect_archive,
)

DEPLOYMENT = ROOT / 'servers/cmi-expedition/deployment'
EVIDENCE = CLIENT.parent / 'evidence/environment-fixes-20261018'
PATCH = '机械动力-远征-0.2.0-test.1-环境与按键修复补丁.zip'
NOTES = '环境与按键修复说明.txt'
ARCHIVE_NOTES = 'Environment-and-Keybind-Fixes-README.txt'
COMMON = (
    'kubejs/startup_scripts/expedition/ShortGrass.js',
    'kubejs/server_scripts/expedition/ShortGrassMigration.js',
    'kubejs/data/biomesoplenty/worldgen/configured_feature/high_grass.json',
    'kubejs/server_scripts/expedition/ExpeditionWeather.js',
)
CLIENT_ONLY = ('kubejs/client_scripts/event/ExpeditionShaderKeyMigration.js',)
KEY_OPTION = 'key_iris.keybind.reload:key.keyboard.f9'
FORBIDDEN = ('EnvironmentFixesProbe.js', 'WeatherRuntimeProbe.js', 'expedition-keybind-migrations.json')


def payloads() -> tuple[dict[str, bytes], dict[str, bytes]]:
    common = {}
    for name in COMMON:
        data = (CLIENT / name).read_bytes()
        assert data == (SERVER / name).read_bytes(), f'Client/server mismatch: {name}'
        assert data == (DEPLOYMENT / name).read_bytes(), f'Deployment mismatch: {name}'
        common[name] = data
    client = {**common, **{name: (CLIENT / name).read_bytes() for name in CLIENT_ONLY}}
    return common, client


def notes() -> bytes:
    return '''机械动力：远征 0.2.0-test.1 · 环境与按键修复补丁

安装前：关闭游戏和服务端，并备份正在使用的存档。
客户端：把补丁内 kubejs 文件夹解压覆盖到当前版本的游戏目录。
服务端：同样覆盖 kubejs；client_scripts 仅在客户端运行，服务端可忽略。
安装后双方都须完整重启，单独 /reload 不能注册启动脚本的 Forge 监听器。

1. 高草挡路
来源是 Biomes O’ Plenty 草原群系的 high_grass / high_grass_plant。
这是实际多格方块柱，并非光影把草拉高。新区块改为普通一格草；
旧区块加载时分批缩短：底部保留一格普通草，上方高草清空，并阻止随机继续生长。
处理只针对上述两种 BOP 方块；不会清理其他植物、农作物或建筑方块。
每 tick 最多扫描 4096 格和检查 32 个区块段，不强制加载任何区块。
相同方块的天然或手种来源无法区分，首次迁移均会缩短。

2. 降低自然降雨频率
主世界天气计时全局共用，各群系决定下雨、下雪或不显示降水。
自然晴天的等待时间延长到原来的 5.75 倍；单次雨天时长保留。
按原版晴雨时长的长期理论均值，降雨发生频率和下雨时间占比约为原来的 20%。
这不是每个群系各自掷 20% 概率，短时间内仍可能遇到连续雨天。
当前已开始的雨会自然结束；手动 /weather 和关闭天气循环的设置保留。

3. R 键冲突
光影重载默认改到 F9，沉浸式飞机保留 R。
旧客户端第一次启动时，若光影重载仍为无修饰键的 R，会迁移到空闲的 F9；
若 F9 已被其他功能占用，则尝试 F6。自行设置过其他键或组合键时予以保留。
新完整包和 HMCL 轻量包使用 F9 的初始设置。
本补丁不包含 options.txt，不覆盖玩家其他画面、音量或按键设置，
也不包含个人按键迁移记录、世界存档或临时诊断脚本。

本补丁未增减模组，适用于 0.2.0-test.1 的现有客户端和服务端。
'''.encode('utf-8-sig')


def fresh_options(data: bytes) -> bytes:
    text = data.decode('utf-8')
    rows = text.splitlines()
    key = KEY_OPTION.split(':', 1)[0] + ':'
    assert sum(line.startswith(key) for line in rows) <= 1
    result = [KEY_OPTION if line.startswith(key) else line for line in rows]
    if not any(line.startswith(key) for line in rows):
        result.append(KEY_OPTION)
    return ('\n'.join(result) + '\n').encode()


def assert_safe_archive(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            assert not any(token in name for token in FORBIDDEN), f'Personal/probe entry: {path.name}:{name}'


def backup(paths: list[Path], phase: str) -> tuple[Path, list[dict]]:
    stamp = datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S-%f')
    root = EVIDENCE / 'backups' / f'{phase}-{stamp}'
    records = []
    for path in paths:
        if path.exists():
            dest = root / path.relative_to(ROOT)
            cow_copy(path, dest)
            records.append({'path': str(path.relative_to(ROOT)), 'backup': str(dest.relative_to(ROOT))})
    return root, records


def update_checksums(hashes: dict[str, str]) -> dict[str, str]:
    main = {}
    for filename in ['SHA256SUMS.txt', 'SHA256SUMS-PC.txt']:
        path = OUT / filename
        rows = {}
        for line in path.read_text().splitlines():
            digest, name = line.split('  ', 1)
            rows[name] = digest
        for name, digest in hashes.items():
            if filename == 'SHA256SUMS.txt' or name in rows or name == PATCH:
                rows[name] = digest
        path.write_text(''.join(f'{digest}  {name}\n' for name, digest in rows.items()))
        if filename == 'SHA256SUMS.txt':
            main = rows
    return main


def metadata(path: Path, package: dict, at: str, files: int | None = None) -> dict:
    value = read_json(path)
    value.update({'updatedAt': at, 'bytes': package['bytes'], 'sha256': package['sha256'],
                  'environmentFixesApplied': True})
    if files is not None:
        value['fileCount' if 'fileCount' in value else 'files'] = files
    for flag in ['archiveIntegrityPassed', 'zipIntegrityPassed']:
        if flag in value:
            value[flag] = True
    return value


def package(mode: str) -> dict:
    common, client = payloads()
    patch_payload = {**client, ARCHIVE_NOTES: notes()}
    plan = {'mode': mode, 'patch': PATCH, 'destination': str(OUT),
            'commonFiles': list(common), 'clientOnlyFiles': list(CLIENT_ONLY),
            'largeArchives': [FULL, LIGHT, CUMULATIVE, SERVER_ZIP],
            'payloadHashes': {name: blob_sha(data) for name, data in client.items()},
            'remoteServicesChanged': False}
    if mode == 'plan':
        return plan
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    at = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    mutable = [OUT / PATCH, OUT / NOTES, OUT / 'SHA256SUMS.txt', OUT / 'SHA256SUMS-PC.txt']
    if mode == 'apply':
        mutable.extend([OUT / name for name in [FULL, LIGHT, CUMULATIVE, SERVER_ZIP,
                      'client-files.json', 'client-build.json', 'light-client-build.json']])
        mutable.append(SERVER_METADATA)
    backup_root, backups = backup(mutable, mode)
    work_root = Path(tempfile.mkdtemp(prefix='packaging-', dir=EVIDENCE))
    try:
        results, stages = {}, {}
        patch_path = work_root / 'patch.zip'
        with zipfile.ZipFile(patch_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(patch_payload.items()):
                archive.writestr(name, data)
        result = inspect_archive(patch_path, patch_payload)
        result.update({'bytes': patch_path.stat().st_size, 'sha256': sha(patch_path)})
        results[PATCH] = result
        stages[PATCH] = patch_path
        json_updates = []
        if mode == 'apply':
            full_options = {}
            for name in [FULL, LIGHT]:
                assert_safe_archive(OUT / name)
                with zipfile.ZipFile(OUT / name) as archive:
                    # Start from the distribution's clean defaults, never the local user's file.
                    full_options[name] = fresh_options(archive.read('overrides/options.txt'))
            assert full_options[FULL] == full_options[LIGHT], 'Fresh option defaults differ'
            client_rows = manifest_rows(read_json(OUT / 'client-files.json'),
                                        {**client, 'options.txt': full_options[FULL]})
            with zipfile.ZipFile(OUT / SERVER_ZIP) as archive:
                server_rows = manifest_rows(json.loads(archive.read('deployment-files.json')), common)
            definitions = [
                (FULL, {'overrides/' + name: data for name, data in client.items()} |
                       {'overrides/options.txt': full_options[FULL]}),
                (LIGHT, {'overrides/' + name: data for name, data in client.items()} |
                        {'overrides/options.txt': full_options[LIGHT]}),
                (CUMULATIVE, {**client, ARCHIVE_NOTES: notes()}),
                (SERVER_ZIP, {**common, 'deployment-files.json': json_bytes(server_rows)}),
            ]
            for index, (name, updates) in enumerate(definitions):
                assert_safe_archive(OUT / name)
                work = work_root / str(index)
                work.mkdir()
                staged = work / 'package.zip'
                results[name] = rewrite_archive(OUT / name, staged, updates, work)
                stages[name] = staged
                assert_safe_archive(staged)
                print(json.dumps({'validated': name, 'bytes': results[name]['bytes']}, ensure_ascii=False), flush=True)
            assert len(client_rows) == results[FULL]['fileCount'] - 2
            assert len(server_rows) == results[SERVER_ZIP]['fileCount'] - 1
            full_meta = metadata(OUT / 'client-build.json', results[FULL], at, len(client_rows))
            light_meta = metadata(OUT / 'light-client-build.json', results[LIGHT], at)
            server_meta = metadata(SERVER_METADATA, results[SERVER_ZIP], at, len(server_rows))
            assert full_meta['modCount'] == results[FULL]['modCount']
            assert light_meta['bundledModCount'] == results[LIGHT]['modCount']
            assert light_meta['downloadedModCount'] + light_meta['bundledModCount'] == light_meta['totalModCount']
            assert server_meta['serverMods'] == results[SERVER_ZIP]['modCount']
            json_updates = [(OUT / 'client-files.json', client_rows), (OUT / 'client-build.json', full_meta),
                            (OUT / 'light-client-build.json', light_meta), (SERVER_METADATA, server_meta)]
        assert payloads() == (common, client), 'Payload changed while packaging'
        for name, staged in stages.items():
            staged.replace(OUT / name)
        for path, value in json_updates:
            path.write_bytes(json_bytes(value))
        (OUT / NOTES).write_bytes(notes())
        checksums = update_checksums({name: value['sha256'] for name, value in results.items()})
        receipt = {**plan, 'at': at, 'backupRoot': str(backup_root), 'backups': backups,
                   'packages': results, 'checksums': checksums,
                   'fullDistributionsUpdated': mode == 'apply'}
        (EVIDENCE / ('release-packaging.json' if mode == 'apply' else 'patch-packaging.json')).write_bytes(json_bytes(receipt))
        (EVIDENCE / 'implementation.json').write_bytes(json_bytes({'at': at, 'files': plan['payloadHashes']}))
        return receipt
    finally:
        shutil.rmtree(work_root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument('--patch', action='store_true', help='Write only the new small patch and notes/checksums')
    actions.add_argument('--apply', action='store_true', help='Synchronize all local release archives after runtime verification')
    args = parser.parse_args()
    print(json.dumps(package('apply' if args.apply else 'patch' if args.patch else 'plan'), ensure_ascii=False, indent=2))
