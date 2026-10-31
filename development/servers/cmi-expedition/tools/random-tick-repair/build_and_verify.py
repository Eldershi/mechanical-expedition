#!/usr/bin/env python3
"""Build isolated scheduler-disable candidates; never replace active mod files."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

TOOL = Path(__file__).resolve().parent
SERVER = TOOL.parents[1]
BUILD = TOOL / "build"
SPECS = [
    {"jar": "Corgilib-Forge-1.20.1-4.0.3.6.jar",
     "sha256": "6f337ceae789bd31f39c0c4e1bfa1bc094dbfcc2d8e4eee3c8b6f50750891298",
     "package": "corgitaco/corgilib", "prefix": "corgilib", "config": "corgilib-common.mixins.json"},
    {"jar": "Oh-The-Trees-Youll-Grow-forge-1.20.1-1.7.3.jar",
     "sha256": "5817a5ff8439515b6413ab655cc7d64ecd3d24d4ac5a8605ae34fd73ec8be4cf",
     "package": "dev/corgitaco/ohthetreesyoullgrow", "prefix": "ohthetreesyoullgrow",
     "config": "ohthetreesyoullgrow.mixins.json"},
]


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def command(args):
    result = subprocess.run([str(arg) for arg in args], capture_output=True, text=True, check=True)
    return result.stdout + result.stderr


def main():
    for name in ("classes", "stub-classes", "work", "analysis", "candidates", "manifests"):
        (BUILD / name).mkdir(parents=True, exist_ok=True)
    original_dir = TOOL / "original"
    original_dir.mkdir(exist_ok=True)
    for spec in SPECS:
        source = SERVER / "instance/mods" / spec["jar"]
        blob = source.read_bytes()
        assert sha(blob) == spec["sha256"], (source, sha(blob))
        backup = original_dir / spec["jar"]
        if backup.exists():
            assert backup.read_bytes() == blob, "Refusing to overwrite differing original"
        else:
            shutil.copy2(source, backup)
    asm = [SERVER / "instance/libraries/org/ow2/asm" / name / "9.8" / f"{name}-9.8.jar"
           for name in ("asm", "asm-tree", "asm-util", "asm-analysis")]
    assert all(path.is_file() for path in asm), asm
    asm_cp = os.pathsep.join(map(str, asm))
    command(["javac", "--release", "17", "-encoding", "UTF-8", "-cp", asm_cp,
             "-d", BUILD / "classes", TOOL / "src/PatchQueue.java"])
    command(["javac", "--release", "17", "-encoding", "UTF-8", "-d", BUILD / "stub-classes",
             TOOL / "tests/net/minecraft/core/BlockPos.java", TOOL / "tests/QueueStubTest.java"])
    patch_cp = os.pathsep.join([str(BUILD / "classes"), str(BUILD / "stub-classes"), asm_cp,
                               *(str(original_dir / spec["jar"]) for spec in SPECS)])
    reports = []
    for spec in SPECS:
        original = (original_dir / spec["jar"]).read_bytes()
        with zipfile.ZipFile(io.BytesIO(original)) as before:
            assert before.testzip() is None
            infos, comment = before.infolist(), before.comment
            names = before.namelist()
            assert len(names) == len(set(names))
            assert not any(name.upper().startswith("META-INF/")
                           and name.upper().endswith((".SF", ".RSA", ".DSA", ".EC")) for name in names)
            members = {name: before.read(name) for name in names}
        config = json.loads(members[spec["config"]])
        new_config = copy.deepcopy(config)
        assert new_config["mixins"].count("chunk.MixinChunkSerializer") == 1
        position = new_config["mixins"].index("chunk.MixinChunkSerializer")
        new_config["mixins"].remove("chunk.MixinChunkSerializer")
        restored = copy.deepcopy(new_config)
        restored["mixins"].insert(position, "chunk.MixinChunkSerializer")
        assert restored == config, "Unrelated mixin configuration changed"
        target_class = spec["package"] + "/mixin/chunk/MixinChunkAccess.class"
        work = BUILD / "work" / spec["prefix"]
        work.mkdir(exist_ok=True)
        before_class, after_class = work / "before.class", work / "after.class"
        before_class.write_bytes(members[target_class])
        verification = command(["java", "-Xverify:all", "-cp", patch_cp, "PatchQueue", before_class,
                                after_class, spec["prefix"] + "$scheduleRandomTick"])
        assert "ASM_CHECK_OK" in verification, verification
        new_members = dict(members)
        new_members[spec["config"]] = (json.dumps(new_config, indent=2) + "\n").encode()
        new_members[target_class] = after_class.read_bytes()
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as after:
            after.comment = comment
            for info in infos:
                after.writestr(copy.copy(info), new_members[info.filename])
                # zipfile supplies default permissions when the original value is zero.
                # Restore that exact central-directory metadata before closing the archive.
                after.getinfo(info.filename).external_attr = info.external_attr
        patched = buffer.getvalue()
        expected_changes = {spec["config"], target_class}
        with zipfile.ZipFile(io.BytesIO(patched)) as checked:
            assert checked.testzip() is None
            assert checked.namelist() == names
            changed = [name for name in names if checked.read(name) != members[name]]
            assert set(changed) == expected_changes, changed
            for old_info in infos:
                new_info = checked.getinfo(old_info.filename)
                assert new_info.date_time == old_info.date_time
                assert new_info.external_attr == old_info.external_attr
            member_report = [{"path": name, "beforeSha256": sha(members[name]),
                              "afterSha256": sha(checked.read(name)), "unchanged": name not in expected_changes}
                             for name in names]
        candidate = BUILD / "candidates" / spec["jar"]
        candidate.write_bytes(patched)
        stub_cp = os.pathsep.join([str(BUILD / "stub-classes"), str(candidate)])
        stub = command(["java", "-Xverify:all", "-Xms16M", "-Xmx64M", "-cp", stub_cp,
                        "QueueStubTest", spec["package"].replace("/", ".") + ".mixin.chunk.MixinChunkAccess",
                        spec["prefix"]])
        assert "QUEUE_STUB_OK" in stub, stub
        for name in ("MixinChunkAccess", "MixinChunkSerializer"):
            clazz = spec["package"].replace("/", ".") + ".mixin.chunk." + name
            disassembly = command(["javap", "-classpath", original_dir / spec["jar"],
                                   "-p", "-c", "-l", clazz])
            (BUILD / "analysis" / (spec["prefix"] + "-original-" + name + ".javap.txt")).write_text(disassembly)
        (BUILD / "analysis" / (spec["prefix"] + "-patched-MixinChunkAccess.javap.txt")).write_text(
            command(["javap", "-classpath", candidate, "-p", "-c", "-l",
                     spec["package"].replace("/", ".") + ".mixin.chunk.MixinChunkAccess"]))
        (BUILD / "analysis" / (spec["prefix"] + "-checks.txt")).write_text(verification + stub)
        report = {"jar": spec["jar"], "originalJar": str(original_dir / spec["jar"]),
                  "candidateJar": str(candidate), "originalSha256": sha(original),
                  "candidateSha256": sha(patched), "bytes": len(patched),
                  "changedZipMembers": changed, "unchangedZipMemberCount": len(names) - 2,
                  "allOtherZipMembersByteIdentical": True, "remainingMixinConfigurationUnchanged": True,
                  "zipIntegrityPassed": True, "asmCheck": verification.strip(), "stubCheck": stub.strip(),
                  "members": member_report}
        (BUILD / "manifests" / (spec["prefix"] + "-integrity.json")).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        reports.append({key: value for key, value in report.items() if key != "members"})
        assert sha((SERVER / "instance/mods" / spec["jar"]).read_bytes()) == spec["sha256"]
    summary = {"passed": True, "candidateOnly": True, "minecraftOrForgeStarted": False,
               "productionModsOrWorldsModified": False, "remoteAccess": False,
               "strategy": "Disable library deferred random-tick enqueue and NBT persistence; preserve registrations",
               "results": reports}
    (BUILD / "verification.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
