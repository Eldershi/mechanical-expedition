"""Package the verified pre-steam recipe/quest overlay as a small local patch."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib
import json
import re
import shutil
import zipfile


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = ROOT / "clients/cmi-expedition/evidence/pre-steam-rollback-20261018"
OUT = ROOT / "releases/0.2.0-test.1"
BACKUP = ROOT / "backups/pre-steam-rollback-20261018"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def without_descriptions(data):
    pattern = r'\bdescription:\s*\[(?:\s*"(?:\\.|[^"\\])*"\s*)*\]\s*'
    text = re.sub(pattern, '', data.decode())
    return re.findall(r'"(?:\\.|[^"\\])*"|[^\s]+', text)


def main():
    implementation = json.loads((EVIDENCE / "implementation.json").read_text())
    successful = []
    for path in EVIDENCE.glob("runtime*-validation.json"):
        candidate = json.loads(path.read_text())
        audits = candidate.get("audits", {})
        if (candidate.get("serverReady") and not candidate.get("timedOut")
            and candidate.get("reason") == "both_audits_written"
            and candidate.get("exitCode") in (0, 143)
            and all(audits.get(name) and audits[name].get("passed") for name in
                    ["expedition-pre-steam-audit.json", "expedition-cmi-smoke.json"])):
            successful.append((path, candidate))
    assert successful, "No successful runtime validation available"
    run_path, run = max(successful, key=lambda row: row[0].stat().st_mtime)
    fixture = EVIDENCE / run_path.name.split("-")[0]
    native = run["audits"]["expedition-pre-steam-audit.json"]
    milestones = run["audits"]["expedition-cmi-smoke.json"]
    assert native and native["passed"] and milestones and milestones["passed"]
    # The disposable fixture can require controlled termination while its
    # world-generation workers finish. Validate loading and actual recipe IDs;
    # do not misreport that termination as a successful graceful shutdown.
    assert run["serverReady"] and not list((fixture / "crash-reports").glob("*.txt"))
    assert not run["recipeFailures"]
    assert all(not row["errors"] and row["summaries"] for row in run["kubejs"].values())
    payload = {}
    for relative, expected in implementation["files"].items():
        blobs = [(ROOT / parent / relative).read_bytes() for parent in [
            "clients/cmi-expedition/instance", "clients/cmi-expedition/overlay", "servers/cmi-expedition/instance"]]
        assert blobs[0] == blobs[1] == blobs[2] and sha(blobs[0]) == expected, relative
        tested = (fixture / relative).read_bytes()
        if tested != blobs[0]:
            # Description text may differ when all non-description fields match.
            # Verify the accepted payload hashes before packaging.
            merge = json.loads((EVIDENCE / "post-runtime-prose-merge.json").read_text())
            assert relative == merge["path"] and sha(tested) == merge["testedSha256"]
            assert sha(blobs[0]) == merge["mergedSha256"] and without_descriptions(tested) == without_descriptions(blobs[0])
        payload[relative] = blobs[0]
    for relative, digest in run["payloadSha256After"].items():
        assert sha(payload[relative]) == digest, f"Runtime checked a different payload: {relative}"
    notes = f"""蒸汽前配方并行与任务精简补丁
适用：机械动力：远征 0.2.0-test.1，Minecraft 1.20.1 / Forge。

改动：
1. 补回蒸汽之前的原版／模组原配方，包括基础冶炼、动能、流体、存储和红石设备。
2. 原有构件物品及所有魔改配方保留，两套配方并行。蒸汽及以后设备配方保留。
3. 删除91个蒸汽前科技引导节点；保留初始套件和通用生存任务。后续任务前置已清理。
4. 原生启用条件继续生效：配方目录225条，运行检查中启用{native['enabled']}条。

安装：退出游戏、关闭服务端，将本压缩包的 config 与 kubejs 两个目录覆盖到客户端的实际游戏目录及服务端根目录，然后重启。客户端和服务端使用相同补丁。
本补丁包含9个配置／脚本文件；machine_learning.snbt 是隐藏空章节，请一并覆盖旧文件。

打包前检查覆盖配方注册、六类构件和15个后期里程碑；这些检查不代替生存全流程验证。
生成补丁不执行远程部署或重打完整发行包。
"""
    note_name = "蒸汽前配方并行说明.txt"
    patch_name = "机械动力-远征-0.2.0-test.1-蒸汽前配方并行补丁.zip"
    payload["补丁说明.txt"] = notes.encode()
    for name in [note_name, patch_name, "SHA256SUMS.txt"]:
        source = OUT / name
        backup = BACKUP / "releases/0.2.0-test.1" / name
        if source.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
    (OUT / note_name).write_text(notes)
    target = OUT / patch_name
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, blob in sorted(payload.items()):
            archive.writestr(relative, blob)
    with zipfile.ZipFile(target) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist()) == set(payload)
        assert all(archive.read(relative) == blob for relative, blob in payload.items())
    checksum = OUT / "SHA256SUMS.txt"
    rows = [line for line in checksum.read_text().splitlines() if not any(line.endswith("  " + name) for name in [patch_name, note_name])]
    rows.extend(sha((OUT / name).read_bytes()) + "  " + name for name in [patch_name, note_name])
    checksum.write_text("\n".join(rows) + "\n")
    implementation.update({"runtimeVerified": True, "nativeEnabled": native["enabled"],
        "nativeSkipped": native["skippedByNativeConditions"], "runtimeEvidence": run_path.name,
        "testShutdown": {"exitCode": run["exitCode"], "gracefulStop": run["gracefulStop"]},
        "patch": str(target.relative_to(ROOT)), "patchSha256": sha(target.read_bytes()),
        "completedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()})
    (EVIDENCE / "implementation.json").write_text(json.dumps(implementation, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"patch": str(target), "bytes": target.stat().st_size,
        "sha256": implementation["patchSha256"], "nativeEnabled": native["enabled"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
