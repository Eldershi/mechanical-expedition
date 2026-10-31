"""Synchronize the reviewed Curios config/KubeJS payload into local releases.

The default invocation is read-only. Run with --apply only after the runtime
checks have passed and implementation.json contains the final payload hashes.
No desktop deliveries, remote operations, or source-instance edits are made.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import tempfile
import zipfile
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "clients/cmi-expedition/instance"
SERVER = ROOT / "servers/cmi-expedition/instance"
OUT = ROOT / "releases/0.2.0-test.1"
EVIDENCE = ROOT / "clients/cmi-expedition/evidence/curios-unification-20261017"
IMPLEMENTATION = EVIDENCE / "implementation.json"
FULL = "机械动力-远征-0.2.0-test.1-Windows客户端.zip"
LIGHT = "机械动力-远征-0.2.0-test.1-HMCL轻量包.mrpack"
CUMULATIVE = "机械动力-远征-0.2.0-test.1-客户端性能累积补丁.zip"
SERVER_ZIP = "mechanical-expedition-0.2.0-test.1-server.zip"
PATCH = "机械动力-远征-0.2.0-test.1-装备槽位整合补丁.zip"
NOTES = "装备槽位整合说明.txt"
ARCHIVE_NOTES = "Curios-Unification-README.txt"
SERVER_METADATA = ROOT / "servers/cmi-expedition/evidence/server-package.json"


def sha(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def blob_sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_payload() -> tuple[dict, dict[str, bytes]]:
    implementation = read_json(IMPLEMENTATION)
    payload: dict[str, bytes] = {}
    for name, expected in implementation["files"].items():
        relative = PurePosixPath(name)
        assert not relative.is_absolute() and ".." not in relative.parts, name
        assert relative.parts[0] in {"config", "kubejs"}, name
        client_data = (CLIENT / name).read_bytes()
        server_data = (SERVER / name).read_bytes()
        assert client_data == server_data, f"Client/server mismatch: {name}"
        assert blob_sha(client_data) == expected, f"Manifest is stale: {name}"
        payload[name] = client_data
    assert payload, "Empty implementation manifest"
    return implementation, payload


def manifest_rows(rows: list[dict], payload: dict[str, bytes]) -> list[dict]:
    indexed = {row["path"]: dict(row) for row in rows}
    assert len(indexed) == len(rows), "Manifest already has duplicate paths"
    for name, data in payload.items():
        indexed[name] = {"path": name, "sha256": blob_sha(data), "bytes": len(data)}
    return [indexed[name] for name in sorted(indexed)]


def cow_copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    assert not destination.exists(), destination
    # macOS/APFS clonefile keeps the multi-GB release backups inexpensive.
    subprocess.run(["/bin/cp", "-c", "-p", str(source), str(destination)], check=True)


def info_signature(info: zipfile.ZipInfo) -> tuple:
    return info.CRC, info.file_size, info.compress_size, info.compress_type


def rewrite_archive(source: Path, staged: Path, updates: dict[str, bytes], work: Path) -> dict:
    with zipfile.ZipFile(source) as archive:
        originals = {entry.filename: info_signature(entry) for entry in archive.infolist()}
        assert len(originals) == len(archive.infolist()), f"Duplicate archive entries: {source}"
        mods = {
            name: signature for name, signature in originals.items()
            if (name.startswith("mods/") or name.startswith("overrides/mods/")) and name.endswith(".jar")
        }
        latest_timestamp = max(
            datetime(*entry.date_time, tzinfo=ZoneInfo("Asia/Shanghai")).timestamp()
            for entry in archive.infolist()
        )
    cow_copy(source, staged)
    members = work / "members"
    members.mkdir(parents=True)
    # Ensure Info-ZIP -u replaces even same-size files from a recent build.
    update_mtime = max(datetime.now().timestamp(), latest_timestamp) + 4
    for name, data in updates.items():
        target = members / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        os.utime(target, (update_mtime, update_mtime))
    result = subprocess.run(
        ["/usr/bin/zip", "-q", "-u", str(staged), *sorted(updates)],
        cwd=members, capture_output=True, text=True,
        env={**os.environ, "TZ": "Asia/Shanghai"},
    )
    if result.returncode:
        raise RuntimeError(f"zip update failed ({source.name}): {result.stdout} {result.stderr}")
    checked = inspect_archive(staged, updates, originals, mods)
    checked["bytes"] = staged.stat().st_size
    checked["sha256"] = sha(staged)
    return checked


def inspect_archive(path: Path, updates: dict[str, bytes], originals=None, mods=None) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        assert len(names) == len(set(names)), f"Duplicate ZIP entries: {path}"
        bad = archive.testzip()
        assert bad is None, f"Corrupt ZIP entry {bad}: {path}"
        entries = {entry.filename: entry for entry in archive.infolist()}
        for name, expected in updates.items():
            assert archive.read(name) == expected, f"Payload mismatch: {path.name}:{name}"
        if originals is not None:
            assert set(entries) == set(originals) | set(updates), f"Unexpected entry changes: {path}"
            for name, signature in originals.items():
                if name not in updates:
                    assert info_signature(entries[name]) == signature, f"Unrelated ZIP entry changed: {name}"
        if mods is not None:
            actual_mods = {
                name: info_signature(info) for name, info in entries.items()
                if (name.startswith("mods/") or name.startswith("overrides/mods/")) and name.endswith(".jar")
            }
            assert actual_mods == mods, f"Mod payload changed: {path}"
        return {
            "archiveIntegrityPassed": True,
            "noDuplicateEntries": True,
            "changedEntryHashesVerified": {name: blob_sha(data) for name, data in updates.items()},
            "unchangedEntriesPreserved": originals is not None,
            "modCount": len(mods) if mods is not None else 0,
            "entryCount": len(names),
            "fileCount": sum(not info.is_dir() for info in entries.values()),
        }


def update_metadata(path: Path, package: dict, at: str, file_count=None) -> dict:
    metadata = read_json(path)
    metadata.update({
        "updatedAt": at,
        "bytes": package["bytes"],
        "sha256": package["sha256"],
        "curiosUnificationApplied": True,
    })
    if file_count is not None:
        metadata["fileCount" if "fileCount" in metadata else "files"] = file_count
    if "archiveIntegrityPassed" in metadata:
        metadata["archiveIntegrityPassed"] = True
    if "zipIntegrityPassed" in metadata:
        metadata["zipIntegrityPassed"] = True
    return metadata


def patch_notes(implementation: dict) -> bytes:
    text = f"""机械动力：远征 0.2.0-test.1 · 装备槽位整合补丁

适用范围：本补丁同时适用于客户端和服务端；双方使用同一补丁。
安装：关闭游戏客户端及服务端，将补丁内容解压覆盖到各自游戏目录。
安装后客户端和服务端均需完整重启，单独 /reload 无法加载启动脚本和槽位配置。

当前布局：{implementation['enabledTypes']} 类已开放槽位，共 {implementation['baseFunctionalSlots']} 个基础功能格。
腰带 2，戒指 10，背饰 1，背包专用 1，头饰 1，项链 3，手镯 2，
手饰/手套合并 2，护符 5，通用饰品 5，构件 1；其他已开放类型各 1。
普通与灾变腰带互通，普通/灾变/天境戒指互通；天境披风、手套、吊坠、饰品
分别进入背饰、手饰、项链、通用饰品，取消独立天境槽位；天境护盾不再可装备。
背包专用格仅收纳六种精妙背包；背包不再占用背饰或通用饰品格。
通用饰品只接纳真正的通用饰品；有专属分类的装备仍使用各自槽位。
上述栏位数量固定；L2、Enigmatic Legacy、Malum 等装备原有的这些栏位
增减效果不再生效，装备的其他属性保留；旧存档中的相关扩容缓存会清理。
灾变护身符、Malum 符文、奥秘卷轴和术石保留 0 个基础格及各自原生解锁机制。

旧存档首次进入时：Curios 原生返还被移除槽位及溢出槽位中的装备；
一次性整理脚本将仍留在错误分类中的装备移到可用的目标空槽，无法放入时返还。
请检查背包和附近掉落物，确认已收回返还的装备。
本补丁仅调整配置和 KubeJS 内容，没有增减模组。
"""
    return text.encode("utf-8-sig")


def package(apply: bool) -> dict:
    implementation, payload = read_payload()
    plan = {
        "apply": apply,
        "payloadFiles": list(payload),
        "payloadBytes": sum(map(len, payload.values())),
        "archives": [FULL, LIGHT, CUMULATIVE, SERVER_ZIP, PATCH],
        "destination": str(OUT),
    }
    if not apply:
        return plan

    at = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    stamp = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y%m%d-%H%M%S-%f")
    backup_root = EVIDENCE / "backups" / ("releases-" + stamp)
    mutable = [
        OUT / name for name in [FULL, LIGHT, CUMULATIVE, SERVER_ZIP, PATCH,
            "client-files.json", "client-build.json", "light-client-build.json",
            "SHA256SUMS.txt", "SHA256SUMS-PC.txt", NOTES]
    ] + [SERVER_METADATA]
    backup_records = []
    for original in mutable:
        if original.exists():
            backup = backup_root / original.relative_to(ROOT)
            cow_copy(original, backup)
            backup_records.append({"path": str(original.relative_to(ROOT)), "backup": str(backup.relative_to(ROOT))})

    client_rows = manifest_rows(read_json(OUT / "client-files.json"), payload)
    with zipfile.ZipFile(OUT / SERVER_ZIP) as archive:
        deployment_rows = manifest_rows(json.loads(archive.read("deployment-files.json")), payload)
    results = {}
    notes = patch_notes(implementation)
    # Stage and fully validate every ZIP before replacing any released archive.
    work_root = Path(tempfile.mkdtemp(prefix="packaging-", dir=EVIDENCE))
    try:
        stages = {}
        for index, (name, prefix, source_payload) in enumerate([
            (FULL, "overrides/", payload),
            (LIGHT, "overrides/", payload),
            (CUMULATIVE, "", {**payload, ARCHIVE_NOTES: notes}),
            (SERVER_ZIP, "", {**payload, "deployment-files.json": json_bytes(deployment_rows)}),
        ]):
            work = work_root / str(index)
            work.mkdir()
            target = work / "package.zip"
            updates = {prefix + key: value for key, value in source_payload.items()}
            results[name] = rewrite_archive(OUT / name, target, updates, work)
            stages[name] = target
            print(json.dumps({"validated": name, "bytes": results[name]["bytes"]}, ensure_ascii=False), flush=True)

        patch = work_root / "patch.zip"
        patch_payload = {**payload, ARCHIVE_NOTES: notes}
        with zipfile.ZipFile(patch, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(patch_payload.items()):
                archive.writestr(name, data)
        results[PATCH] = inspect_archive(patch, patch_payload)
        results[PATCH].update({"bytes": patch.stat().st_size, "sha256": sha(patch)})
        stages[PATCH] = patch

        full_metadata = update_metadata(OUT / "client-build.json", results[FULL], at, len(client_rows))
        light_metadata = update_metadata(OUT / "light-client-build.json", results[LIGHT], at)
        server_metadata = update_metadata(SERVER_METADATA, results[SERVER_ZIP], at, len(deployment_rows))
        assert full_metadata["modCount"] == results[FULL]["modCount"]
        assert light_metadata["bundledModCount"] == results[LIGHT]["modCount"]
        assert light_metadata["downloadedModCount"] + light_metadata["bundledModCount"] == light_metadata["totalModCount"]
        assert server_metadata["serverMods"] == results[SERVER_ZIP]["modCount"]
        # Manifest sizes must continue to cover exactly the packaged payload.
        assert len(client_rows) == results[FULL]["fileCount"] - 2
        assert len(deployment_rows) == results[SERVER_ZIP]["fileCount"] - 1

        # Do not publish a package if another agent changed the tested payload.
        current_implementation, current_payload = read_payload()
        assert current_implementation["files"] == implementation["files"] and current_payload == payload

        for name, staged in stages.items():
            staged.replace(OUT / name)
        for path, value in [
            (OUT / "client-files.json", client_rows),
            (OUT / "client-build.json", full_metadata),
            (OUT / "light-client-build.json", light_metadata),
            (SERVER_METADATA, server_metadata),
        ]:
            path.write_bytes(json_bytes(value))
        (OUT / NOTES).write_bytes(notes)
        all_archives = sorted(p for p in OUT.iterdir() if p.suffix in {".zip", ".mrpack"})
        known_hashes = {name: result["sha256"] for name, result in results.items()}
        checksums = {path.name: known_hashes.get(path.name) or sha(path) for path in all_archives}
        (OUT / "SHA256SUMS.txt").write_text("".join(f"{digest}  {name}\n" for name, digest in checksums.items()))
        (OUT / "SHA256SUMS-PC.txt").write_text("".join(f"{checksums[name]}  {name}\n" for name in [FULL, LIGHT, CUMULATIVE, PATCH]))
        # Recheck the implementation snapshot in case tests changed source files.
        current_implementation, current_payload = read_payload()
        assert current_implementation["files"] == implementation["files"] and current_payload == payload
        receipt = {
            **plan,
            "at": at,
            "backupRoot": str(backup_root),
            "backups": backup_records,
            "baseFunctionalSlots": implementation.get("baseFunctionalSlots"),
            "enabledTypes": implementation.get("enabledTypes"),
            "payloadHashes": implementation["files"],
            "packages": results,
            "clientManifestFiles": len(client_rows),
            "serverManifestFiles": len(deployment_rows),
            "clientModCount": full_metadata["modCount"],
            "serverModCount": server_metadata["serverMods"],
            "checksums": checksums,
            "desktopDeliveryChanged": False,
            "remoteServicesChanged": False,
        }
        (EVIDENCE / "release-packaging.json").write_bytes(json_bytes(receipt))
        return receipt
    finally:
        shutil.rmtree(work_root)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Apply only after runtime tests pass")
    args = parser.parse_args()
    print(json.dumps(package(args.apply), ensure_ascii=False, indent=2))
