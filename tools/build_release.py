"""Build a reproducible client mrpack and a separate, source-only update repository."""

import argparse
import csv
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
from urllib.parse import quote, urlsplit, urlunsplit, unquote
import zipfile


HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
INSTANCE = PROJECT / "instance"
BASE = PROJECT.parent / "cmi-beta/instance"
PREFIXES = ("config/", "kubejs/", "defaultconfigs/", "resourcepacks/", "hotai/", "ldlib/")
ROOT_FILES = {"LICENSE", "License.md", "icon.png", "optional_jvm.txt"}


def hash_file(path, algorithm="sha256"):
    return hashlib.new(algorithm, path.read_bytes()).hexdigest()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def https_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        raise ValueError(f"Expected public HTTPS download URL: {url}")
    return urlunsplit((parts.scheme, parts.netloc, quote(unquote(parts.path), safe="/:@+"), parts.query, ""))


def validate_path(relative):
    path = PurePosixPath(relative)
    if path.is_absolute() or any(part in {".", ".."} for part in path.parts) or any(c in relative for c in "\\\t\r\n:"):
        raise ValueError(f"Unsafe publication path: {relative}")


def zip_files(destination, entries):
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, content, executable in sorted(entries):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 16, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if executable else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)


def build(config_path, output):
    config = json.loads(config_path.read_text())
    if config["packId"] != "mechanical-expedition":
        raise ValueError("Unexpected pack ID")
    if config["repository"]:
        https_url(config["repository"])
    commit = subprocess.check_output(["git", "-C", str(BASE), "rev-parse", "HEAD"], text=True).strip()
    if commit != config["baseCommit"]:
        raise ValueError("The installed baseline commit changed; review the distribution base first")
    if output.exists():
        marker = output / "build.json"
        if not marker.exists() or json.loads(marker.read_text())["packId"] != config["packId"]:
            raise ValueError(f"Refusing to replace unrelated directory: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    dump(output / "build.json", {"packId": config["packId"], "version": config["version"], "status": "building"})
    repository = output / "repository"
    pack = repository / "pack"
    pack.mkdir(parents=True)

    tracked = subprocess.check_output(["git", "-C", str(BASE), "ls-files", "-z"]).decode().split("\0")
    published = []
    for relative in tracked:
        if not relative or not (relative.startswith(PREFIXES) or relative in ROOT_FILES):
            continue
        validate_path(relative)
        source = INSTANCE / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError(f"Tracked release input missing or symlinked: {relative}")
        # Tracked upstream content only: caches, personal files and saves are never selected.
        target = pack / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        published.append(relative)
    overlay = json.loads((PROJECT / "evidence/overlay-files.json").read_text())
    for relative, expected_hash in overlay.items():
        validate_path(relative)
        source = INSTANCE / relative
        if hash_file(source) != expected_hash:
            raise ValueError(f"Overlay changed without a recorded review: {relative}")
        target = pack / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    for source in sorted((HERE / "player").iterdir()):
        if source.is_file():
            target = pack / "updater" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if source.suffix in {".sh", ".command"}:
                target.chmod(0o755)
    settings = {
        "PACK_ID": config["packId"], "REMOTE_URL": config["repository"], "REF": config["ref"],
        "MINECRAFT": config["minecraft"], "FORGE": config["forge"],
    }
    (pack / "updater/expedition.conf").write_text("\n".join(f"{key}={value}" for key, value in settings.items()) + "\n")
    release = {
        "PACK_ID": config["packId"], "VERSION": config["version"], "CHANNEL": config["channel"],
        "MINECRAFT": config["minecraft"], "FORGE": config["forge"],
    }
    (repository / "release.env").write_text("\n".join(f"{key}={value}" for key, value in release.items()) + "\n")
    dump(pack / "pack-info.json", {**config, "base": "Create: Mechanisms and Innovations Beta 2.5.0", "distribution": "client", "status": "development_test"})
    upstream = (
        "# 上游来源\n\n"
        "本整合包为“机械动力：远征”修改版，基于 Re_Construction / Team Nebula 的革新构件。\n\n"
        f"- 上游项目：{config['baseRepository']}\n"
        f"- 固定基线：{config['baseCommit']}\n"
        "- 原 LICENSE 和 License.md 随包保留；本修改版不收取下载或分发费用。\n"
        "- 模组由作者公开地址下载；定制 JAR 的内容与固定基线的公开 Git 对象逐字节比对。\n"
        "- 我们的改动：远征科技总览、里程碑审计、独立分发清单和受管文件更新器。\n"
        "- 这是一份开发测试版本，尚未移植完整五心与全部无限构件后期内容。\n"
    )
    (pack / "UPSTREAM.md").write_text(upstream)
    (pack / "README.md").write_text((HERE / "PLAYER-GUIDE.md").read_text())

    sources = {}
    for row in csv.reader((BASE / "updater/update.tsv").read_text().splitlines(), delimiter="\t"):
        if len(row) < 3 or not row[1]:
            continue
        expected, relative, url = row[:3]
        source = INSTANCE / relative
        if not source.exists() or hash_file(source, "sha1") != expected:
            continue
        sources[relative] = {"url": https_url(url), "origin": "upstream_manifest"}
    # Fixed public Git objects cover upstream's bundled custom mods and two omitted utilities.
    for relative in tracked:
        if not relative.startswith("mods/") or not relative.endswith(".jar"):
            continue
        if not (INSTANCE / relative).exists():
            continue
        blob = subprocess.check_output(["git", "-C", str(BASE), "show", f"{commit}:{relative}"])
        if hashlib.sha256(blob).hexdigest() != hash_file(INSTANCE / relative):
            raise ValueError(f"Bundled JAR differs from the public Git baseline: {relative}")
        if relative not in sources:
            url = f"https://raw.githubusercontent.com/Eternal-Snowstorm/Create-Mechanism-and-Innovation/{commit}/{quote(relative, safe='/')}"
            sources[relative] = {"url": url, "origin": "public_upstream_git", "commit": commit}
    fixes = json.loads((PROJECT.parent / "cmi-beta/evidence/local-fixes.json").read_text())
    for fix in fixes:
        relative = "mods/" + Path(fix["file"]).name
        if (INSTANCE / relative).exists() and relative not in sources:
            if hash_file(INSTANCE / relative, "sha1") != fix["sha1"]:
                raise ValueError(f"Local dependency fix hash mismatch: {relative}")
            sources[relative] = {"url": https_url(fix["download"]), "origin": "public_dependency_fix", "page": fix["source"]}
    for extra in config.get("additionalSources", []):
        relative = extra["path"]
        validate_path(relative)
        if not relative.startswith("mods/") or not relative.endswith(".jar"):
            raise ValueError("Additional source must name one mod JAR")
        if hash_file(INSTANCE / relative) != extra["sha256"]:
            raise ValueError(f"Additional source checksum mismatch: {relative}")
        sources[relative] = {"url": https_url(extra["url"]), "origin": "explicit_release_source"}
    mods = []
    for source in sorted((INSTANCE / "mods").glob("*.jar")):
        relative = "mods/" + source.name
        if relative not in sources:
            raise ValueError(f"No verified public source for {relative}")
        mods.append({
            "path": relative, "hashes": {kind: hash_file(source, kind) for kind in ("sha1", "sha256", "sha512")},
            "downloads": [sources[relative]["url"]], "fileSize": source.stat().st_size,
            "env": {"client": "required", "server": "unsupported"},
        })
    dump(pack / "SOURCE.json", {
        "baseRepository": config["baseRepository"], "baseCommit": commit,
        "sources": sources,
        "note": "Public source mapping only; no QQ exports, account data, saved worlds or local logs.",
    })
    code_files = sorted(path for path in pack.rglob("*") if path.is_file())
    file_rows = [(hash_file(path), path.relative_to(pack).as_posix()) for path in code_files]
    (repository / "files.tsv").write_text("".join(f"{digest}\t{relative}\n" for digest, relative in file_rows))
    (repository / "mods.tsv").write_text("".join(f"{mod['hashes']['sha256']}\t{mod['path']}\t{mod['downloads'][0]}\n" for mod in mods))
    state = sorted(file_rows + [(mod["hashes"]["sha256"], mod["path"]) for mod in mods])
    state_text = "".join(f"{digest}\t{relative}\n" for digest, relative in state)
    dump(repository / "source-manifest.json", config)
    (repository / "README.md").write_text((HERE / "RELEASE-GUIDE.md").read_text())
    shutil.copy2(HERE / "RELEASE-NOTES.md", repository / "RELEASE-NOTES.md")
    workflow = repository / ".github/workflows/release.yml"
    workflow.parent.mkdir(parents=True)
    shutil.copy2(HERE / "release-workflow.yml", workflow)
    shutil.copy2(BASE / "LICENSE", repository / "LICENSE")
    shutil.copy2(BASE / "License.md", repository / "License.md")
    shutil.copy2(pack / "UPSTREAM.md", repository / "UPSTREAM.md")
    (repository / ".gitignore").write_text("dist/\n.DS_Store\n__pycache__/\n*.pyc\n")
    (repository / ".gitattributes").write_text("# Preserve exact release bytes and hashes on every OS.\n* -text\n")
    tools = repository / "tools"
    tools.mkdir()
    for name in ("build_release.py", "test_updater.py", "package_repository.py"):
        if (HERE / name).exists():
            shutil.copy2(HERE / name, tools / name)

    index = {
        "formatVersion": 1, "game": "minecraft", "versionId": config["version"], "name": config["name"],
        "summary": "基于革新构件的远征开发测试版；独立更新源与科技总览。",
        "files": mods, "dependencies": {"minecraft": config["minecraft"], "forge": config["forge"]},
    }
    dump(repository / "modrinth.index.json", index)
    entries = [("modrinth.index.json", (json.dumps(index, ensure_ascii=False, indent=2) + "\n").encode(), False)]
    entries += [("overrides/" + path.relative_to(pack).as_posix(), path.read_bytes(), path.suffix in {".sh", ".command"}) for path in code_files]
    entries += [("overrides/.expedition/state.tsv", state_text.encode(), False), ("overrides/.expedition/installed.env", (repository / "release.env").read_bytes(), False)]
    package = output / f"mechanical-expedition-{config['version']}.mrpack"
    zip_files(package, entries)
    source_zip = output / f"mechanical-expedition-{config['version']}-source.zip"
    zip_files(source_zip, [(path.relative_to(repository).as_posix(), path.read_bytes(), path.suffix in {".sh", ".command"}) for path in repository.rglob("*") if path.is_file()])
    report = {
        "packId": config["packId"], "version": config["version"], "minecraft": config["minecraft"], "forge": config["forge"],
        "managedContentFiles": len(code_files), "modFiles": len(mods), "repositoryConfigured": bool(config["repository"]),
        "package": package.name, "packageSha256": hash_file(package), "packageBytes": package.stat().st_size,
        "sourcePackage": source_zip.name, "sourceSha256": hash_file(source_zip),
        "sources": {origin: sum(s["origin"] == origin for key, s in sources.items() if any(m["path"] == key for m in mods)) for origin in {s["origin"] for s in sources.values()}},
        "privacy": "tracked public base content + reviewed overlay only; personal data excluded",
        "status": "built_local_candidate",
        "formatNotes": "Standard client mrpack for supporting launchers; ForgeCDN download URLs mean this is not a Modrinth-hosting submission bundle.",
    }
    dump(output / "build.json", report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=HERE / "config.json")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text())
    build(args.config, args.output or HERE / "dist" / cfg["version"])
