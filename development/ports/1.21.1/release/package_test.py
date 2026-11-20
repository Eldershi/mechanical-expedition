#!/usr/bin/env python3
"""Snapshot and build the isolated test client and dedicated-server overlay."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
TARGET = ("1.21.1", "21.1.267", 21)
sys.path.insert(0, str(ROOT / "tools"))
from publication_filter import privacy, skip_reason
ASSET_DIRS = {"config", "defaultconfigs", "datapacks", "ldlib2", "kubejs", "hotai",
              "patchouli_books", "tlm_custom_pack", "moonlight-global-datapacks", "resourcepacks"}
KUBEJS_DIRS = {"assets", "data", "config", "startup_scripts", "server_scripts", "client_scripts"}
PRIVATE = {"oeb", "oei", "oef", "exports", "saves", "local", "logs", "screenshots", "vintagestore",
           "exported", "cache", "backups", "local-only", "accounts", "layout_editor", "playerdata", "terrain"}
PRIVATE_PACK = re.compile(r"(?i)(?:create[_ -]?mcgui|expedition.*(?:hnn|hud)|original.predictions|yellow.apple)")
SAFE_DOWNLOADS = {"cdn.modrinth.com", "edge.forgecdn.net", "mediafilez.forgecdn.net",
                  "media.forgecdn.net", "github.com", "maven.neoforged.net"}


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args], text=True).strip()


def manifest():
    value = json_file(ROOT / "source-manifest.json")
    if (value.get("minecraft"), value.get("neoforge"), value.get("java")) != TARGET:
        raise ValueError("Expected Minecraft 1.21.1, NeoForge 21.1.267 and Java 21")
    if value.get("ref") != "migration/1.21.1-neoforge" or value.get("packId") != "mechanical-expedition-neoforge":
        raise ValueError("The test pack needs its own branch and pack ID")
    if not re.fullmatch(r"1\.21\.1-test\.[1-9][0-9]*", value["version"]):
        raise ValueError("Invalid 1.21.1 test version")
    if git("branch", "--show-current") != value["ref"]:
        if git("tag", "--points-at", "HEAD").splitlines().count("v" + value["version"]) != 1:
            raise ValueError("Build from the NeoForge branch or its matching test tag")
        subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", "HEAD",
                        "origin/" + value["ref"]], check=True)
    return value


def fingerprints(path):
    hashes = {name: hashlib.new(name) for name in ("sha1", "sha256", "sha512")}
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            for algorithm in hashes.values():
                algorithm.update(block)
    return {name: algorithm.hexdigest() for name, algorithm in hashes.items()}


def excluded(relative):
    parts = relative.parts
    name = relative.name
    return (
        any(part.startswith(".") or part.lower() in PRIVATE for part in parts)
        or name.lower().startswith("agents")
        or name.lower().endswith((".log", ".bak", ".old", ".db", ".tmp", ".sqlite"))
        or re.search(r"(?i)(?:last_world|activity\.json|fingerprint|bookmark|servers\.dat|resourceful-config-web)", name)
        or (name.endswith(".zip") and PRIVATE_PACK.search(name))
        or (parts[0] == "kubejs" and len(parts) > 1 and parts[1] not in KUBEJS_DIRS)
        or (parts[:2] == ("config", "spark") and name != "config.json")
    )


def external_client_resources():
    directory = ROOT / "integrations/resourcepacks"
    for name in ("create-mcgui.json", "create-style-hnn.json", "neoforge-resourcepacks.json"):
        yield from json_file(directory / name)["clientFiles"]


def selected(instance, client=False):
    external_paths = {file["path"] for file in external_client_resources()} if client else set()
    if client:
        defaults = Path(__file__).with_name("client-options.txt")
        yield Path("options.txt"), defaults.read_bytes()
    for folder in sorted(ASSET_DIRS):
        for path in sorted((instance / folder).rglob("*")):
            relative = path.relative_to(instance)
            if relative.as_posix() in external_paths:
                continue
            if path.is_symlink() or not path.is_file() or excluded(relative) or skip_reason(relative.as_posix()):
                continue
            if relative.parts[-2:] == ("paxi", "resourcepack_load_order.json"):
                order = json_file(path)
                order["loadOrder"] = [value for value in order.get("loadOrder", [])
                                      if not PRIVATE_PACK.search(value) or value == "create_mcGUI_2.10.0.zip"]
                yield relative, (json.dumps(order, indent=2) + "\n").encode()
            else:
                payload, _ = privacy(relative.as_posix(), path.read_bytes())
                if payload is not None:
                    yield relative, payload


def known_downloads(inputs):
    records = {}

    def collect(value):
        if isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            url = value.get("url") or value.get("downloadUrl")
            sha1 = value.get("sha1")
            filename = value.get("filename") or value.get("fileName")
            if isinstance(url, str) and isinstance(sha1, str) and isinstance(filename, str):
                address = urlsplit(url)
                github_release = address.hostname != "github.com" or "/releases/download/" in address.path
                if address.scheme == "https" and address.hostname in SAFE_DOWNLOADS and github_release and not address.query:
                    records[(filename, sha1.lower())] = url
            for item in value.values():
                collect(item)

    for path in inputs:
        collect(json_file(path))
    return records


def mod_inputs(instance):
    choices = sorted((instance / "mods").glob("*.jar"))
    choices = [f for f in choices if not f.is_symlink() and not re.search(r"(?i)expedition.*(?:-qa-|proof|probe)", f.name)]
    names = {p.name for p in choices}
    for required in ("adastra-1.21.1-1.16.26-neoforge.jar", "createcraftedbeginning-0.1.1.jar",
                     "expedition-space-neoforge-1.0.0.jar"):
        if required not in names:
            raise ValueError(f"Missing tested NeoForge input: {required}")
    return choices


def snapshot(instance, downloads, client=False):
    mods = []
    for file in mod_inputs(instance):
        hashes = fingerprints(file)
        row = {"filename": file.name, "bytes": file.stat().st_size, **hashes}
        url = downloads.get((file.name, hashes["sha1"]))
        if url:
            row["downloadUrl"] = url
        mods.append(row)
    files = {relative.as_posix(): hashlib.sha256(data).hexdigest()
             for relative, data in selected(instance, client=client)}
    return {"files": files, "mods": mods}


def check_server(server):
    libraries = server / "libraries/net/neoforged/neoforge"
    if not (libraries / TARGET[1] / "unix_args.txt").is_file():
        raise ValueError("Supply the tested NeoForge 21.1.267 dedicated-server instance")


def zip_entry(archive, name, payload):
    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, payload)


def index_for(meta, lock):
    files = [{"path": "mods/" + row["filename"],
              "hashes": {key: row[key] for key in ("sha1", "sha512")},
              "downloads": [row["downloadUrl"]], "fileSize": row["bytes"],
              "env": {"client": "required", "server": "unsupported"}}
             for row in lock["mods"] if row.get("downloadUrl")]
    for file in external_client_resources():
        files.append({"path": file["path"], "hashes": {key: file[key] for key in ("sha1", "sha512")},
                      "downloads": [file["downloadUrl"]], "fileSize": file["bytes"],
                      "env": {"client": "required", "server": "unsupported"}})
    return {"formatVersion": 1, "game": "minecraft", "versionId": meta["version"],
            "name": "机械动力：远征 · NeoForge 测试",
            "files": files, "dependencies": {key: meta[key] for key in ("minecraft", "neoforge")}}


def build_archive(output, instance, lock, meta, client):
    overlay = dict(selected(instance, client=client))
    if {name.as_posix(): hashlib.sha256(data).hexdigest() for name, data in overlay.items()} != lock["files"]:
        raise ValueError(f"{'Client' if client else 'Server'} configuration snapshot differs from its lock")
    mods = {p.name: p for p in mod_inputs(instance)}
    if set(mods) != {row["filename"] for row in lock["mods"]}:
        raise ValueError("Mod inventory differs from its lock")
    prefix = "overrides/" if client else ""
    for row in lock["mods"]:
        name = f"mods/{row['filename']}"
        actual = mods[row["filename"]]
        if fingerprints(actual) != {k: row[k] for k in ("sha1", "sha256", "sha512")} or actual.stat().st_size != row["bytes"]:
            raise ValueError(f"Mod hash mismatch: {actual.name}")
        if not client or not row.get("downloadUrl"):
            overlay[Path(name)] = actual
    if client:
        info = index_for(meta, lock)
        if info != json_file(ROOT / "modrinth.index.json"):
            raise ValueError("The published Modrinth index differs from its component lock")
    with zipfile.ZipFile(output, "w") as archive:
        if client:
            zip_entry(archive, "modrinth.index.json", json.dumps(info, ensure_ascii=False, indent=2).encode())
        zip_entry(archive, prefix + "expedition-test.json", json.dumps(meta, indent=2).encode())
        for name, data in sorted(overlay.items()):
            zip_entry(archive, prefix + name.as_posix(), data.read_bytes() if isinstance(data, Path) else data)
    return f"{fingerprints(output)['sha256']}  {output.name}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["validate", "lock", "package"])
    parser.add_argument("--client", type=Path)
    parser.add_argument("--server", type=Path)
    parser.add_argument("--catalog", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    meta = manifest()
    if args.action == "validate":
        lock = json_file(ROOT / "current/mods.lock.json")
        index = json_file(ROOT / "modrinth.index.json")
        if lock["version"] != meta["version"] or index["versionId"] != meta["version"]:
            raise ValueError("Test manifest, mod lock and Modrinth index must match")
        if index["dependencies"] != {key: meta[key] for key in ("minecraft", "neoforge")}:
            raise ValueError("Modrinth index must target the test NeoForge version")
        print(meta["version"])
        return
    if not args.client or not args.server:
        parser.error("--client and --server are required")
    check_server(args.server)
    lock_path = ROOT / "current/mods.lock.json"
    if args.action == "lock":
        downloads = known_downloads(args.catalog)
        client = snapshot(args.client, downloads, client=True)
        server = snapshot(args.server, downloads)
        write_json(lock_path, {"version": meta["version"], "minecraft": meta["minecraft"],
                               "neoforge": meta["neoforge"], "client": client, "server": server})
        write_json(ROOT / "modrinth.index.json", index_for(meta, client))
        return
    if not args.output:
        parser.error("--output is required")
    lock = json_file(lock_path)
    if lock["version"] != meta["version"]:
        raise ValueError("The input lock is for a different test version")
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output) as work:
        work = Path(work)
        prefix = f"mechanical-expedition-{meta['version']}"
        client_hash = build_archive(work / f"{prefix}.mrpack", args.client, lock["client"], meta, True)
        server_hash = build_archive(work / f"{prefix}-server.zip", args.server, lock["server"], meta, False)
        (work / "SHA256SUMS").write_text(client_hash + "\n" + server_hash + "\n")
        for item in work.iterdir():
            shutil.move(item, args.output / item.name)
    print(client_hash + "\n" + server_hash)


if __name__ == "__main__":
    main()
