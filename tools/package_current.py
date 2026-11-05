#!/usr/bin/env python3
"""Build the current client as a Modrinth-format pack from verified inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.2.0-dev.1"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def safe_path(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or ".." in path.parts or "\\" in value or path.as_posix() != value:
        raise ValueError(f"Unsafe path: {value}")
    return path


def build(output, bundle_path=None):
    lock = json.loads((ROOT / "current/mods.lock.json").read_text())
    integration = json.loads((ROOT / "integrations/resourcepacks/create-style-dyson.json").read_text())
    release = integration["release"]
    if bundle_path:
        bundle = bundle_path.read_bytes()
    else:
        request = urllib.request.Request(release["clientBundleURL"], headers={"User-Agent": "Mechanical-Expedition-pack-builder"})
        with urllib.request.urlopen(request, timeout=120) as response:
            bundle = response.read()
    if sha256(bundle) != release["clientBundleSHA256"]:
        raise ValueError("Dyson bundle hash mismatch")
    external = {}
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        for item in integration["clientFiles"]:
            name = str(safe_path(item["path"]))
            data = archive.read(name)
            if sha256(data) != item["sha256"] or len(data) != item["bytes"]:
                raise ValueError(f"Dyson file hash mismatch: {name}")
            external[name] = data

    entries = {}
    for line in (ROOT / "current/files.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        if not name.startswith("current/client/"):
            continue
        relative = str(safe_path(name.removeprefix("current/client/")))
        data = (ROOT / name).read_bytes()
        if sha256(data) != expected:
            raise ValueError(f"Client file hash mismatch: {relative}")
        entries[relative] = data

    index_files = []
    names = set()
    for mod in lock["mods"]:
        name = str(safe_path("mods/" + mod["filename"]))
        if name in names:
            raise ValueError(f"Duplicate mod: {name}")
        names.add(name)
        if name in entries or name in external:
            data = entries.get(name, external.get(name))
            if sha256(data) != mod["sha256"] or len(data) != mod["bytes"]:
                raise ValueError(f"Bundled mod hash mismatch: {name}")
        elif mod.get("downloadUrl", "").startswith("https://"):
            index_files.append({"path": name, "hashes": {"sha1": mod["sha1"], "sha512": mod["sha512"]},
                                "downloads": [mod["downloadUrl"]], "fileSize": mod["bytes"],
                                "env": {"client": "required", "server": "unsupported"}})
        else:
            raise ValueError(f"No source for mod: {name}")
    for name, data in external.items():
        if name in entries:
            raise ValueError(f"Duplicate integration file: {name}")
        entries[name] = data
    index = {"formatVersion": 1, "game": "minecraft", "versionId": VERSION,
             "name": "机械动力：远征", "summary": "Mechanical Expedition current client",
             "files": index_files, "dependencies": {"minecraft": lock["minecraft"], "forge": lock["forge"]}}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        def write(name, data):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
        write("modrinth.index.json", (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode())
        for name, data in sorted(entries.items()):
            write("overrides/" + name, data)
    print(json.dumps({"path": str(output), "sha256": sha256(output.read_bytes()),
                      "mods": len(names), "downloadedMods": len(index_files), "overrideFiles": len(entries)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / f"mechanical-expedition-{VERSION}.mrpack")
    parser.add_argument("--dyson-bundle", type=Path)
    args = parser.parse_args()
    build(args.output, args.dyson_bundle)
