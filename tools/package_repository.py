"""Rebuild a distributable client mrpack from the published update repository alone."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import zipfile


def write_zip(path, entries):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for relative, data, executable in sorted(entries):
            info = zipfile.ZipInfo(relative, (2026, 10, 16, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)


def package(repository, output):
    metadata = json.loads((repository / "source-manifest.json").read_text())
    index_bytes = (repository / "modrinth.index.json").read_bytes()
    index = json.loads(index_bytes)
    if index["versionId"] != metadata["version"] or index["dependencies"] != {"minecraft": metadata["minecraft"], "forge": metadata["forge"]}:
        raise ValueError("Package metadata differs from release configuration")
    pack = repository / "pack"
    entries = [("modrinth.index.json", index_bytes, False)]
    state = []
    for line in (repository / "files.tsv").read_text().splitlines():
        expected, relative = line.split("\t")
        if PurePosixPath(relative).is_absolute() or ".." in PurePosixPath(relative).parts or "\\" in relative:
            raise ValueError("Unsafe path")
        path = pack / relative
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Release file differs from manifest: {relative}")
        entries.append(("overrides/" + relative, path.read_bytes(), path.suffix in {".sh", ".command"}))
        state.append((expected, relative))
    mod_rows = {}
    for line in (repository / "mods.tsv").read_text().splitlines():
        expected, relative, url = line.split("\t")
        mod_rows[relative] = (expected, url)
        state.append((expected, relative))
    if set(mod_rows) != {mod["path"] for mod in index["files"]}:
        raise ValueError("Mod lists differ")
    for mod in index["files"]:
        if mod_rows[mod["path"]] != (mod["hashes"]["sha256"], mod["downloads"][0]):
            raise ValueError("Mod source or hash differs")
    entries.append(("overrides/.expedition/state.tsv", "".join(f"{h}\t{p}\n" for h, p in sorted(state)).encode(), False))
    entries.append(("overrides/.expedition/installed.env", (repository / "release.env").read_bytes(), False))
    output.mkdir(parents=True, exist_ok=True)
    destination = output / f"mechanical-expedition-{metadata['version']}.mrpack"
    write_zip(destination, entries)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    destination = package(args.repository, args.output or args.repository / "dist")
    print(json.dumps({"package": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
