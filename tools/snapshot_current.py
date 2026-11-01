#!/usr/bin/env python3
"""Snapshot the active client and deployment overlays with verified mod hashes."""

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import sys
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import parse_qsl, urlsplit

sys.dont_write_bytecode = True
PATCHED_DEPENDENCIES = (
    "ars_controle-1.20.1-1.1.1.jar",
    "1.20.1-maid_storage_manager-1.15.6.jar",
    "MultiBuilderTool-1.20.1-1.0.28.jar",
    "Create-Steam-Ages-1.0-expedition-steamletters-compat.jar",
)


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def digest(blob):
    return hashlib.sha256(blob).hexdigest()


def production_exclusion(relative):
    path = PurePosixPath(relative)
    name = path.name.lower()
    if relative == "config/jei_mekanism_multiblocks-saved_data.nbt":
        return "runtime recipe-viewer cache"
    if ".before-" in name or ".before_" in name:
        return "configuration backup"
    if name == "resetplayerspawn20261018.js":
        return "one-time world migration script"
    if ".disabled" in name:
        return "disabled file"
    if path.suffix.lower() == ".js" and (
        any(word in name for word in ("audit", "probe", "diagnostic"))
        or name.startswith("zz")
        or name in {"test.js", "tests.js"}
        or name.endswith(("_test.js", "-test.js"))
    ):
        return "test, audit or diagnostic script"
    if path.suffix.lower() == ".jar" and any(
        word in name for word in ("probe", "audit", "prototype", "diagnostic")
    ):
        return "non-production instrumentation jar"
    return None


def public_url(value):
    if not isinstance(value, str) or not value:
        return None
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    if any(re.search(r"token|secret|password|signature|credential|authorization", key, re.I)
           for key, _ in parse_qsl(parsed.query)):
        return None
    return value


def read_stable(path):
    for _ in range(3):
        before = path.stat()
        blob = path.read_bytes()
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
            return blob
    raise RuntimeError(f"Source changed while reading: {path.name}")


def hashes(path):
    for _ in range(3):
        before = path.stat()
        values = {name: hashlib.new(name) for name in ("sha1", "sha256", "sha512")}
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                for value in values.values():
                    value.update(block)
        after = path.stat()
        if (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns):
            return {name: value.hexdigest() for name, value in values.items()}, after.st_size
    raise RuntimeError(f"Mod changed while hashing: {path.name}")


def external_resource_files(project, active):
    """Verify enabled external files and reject active files for disabled integrations."""
    roots = [Path(__file__).resolve().parents[1] / "integrations/resourcepacks",
             project / "integrations/resourcepacks",
             project / "clients/cmi-expedition/distribution/repository/integrations/resourcepacks"]
    result = {}
    seen = set()
    for root in roots:
        root = root.resolve()
        if root in seen:
            continue
        seen.add(root)
        for manifest in sorted(root.glob("*.json")):
            if manifest.is_symlink():
                raise RuntimeError("External integration manifest must not be a symlink")
            metadata = json.loads(read_stable(manifest))
            if not isinstance(metadata, dict):
                raise RuntimeError("External integration manifest must be an object")
            enabled = metadata.get("enabled", True)
            if not isinstance(enabled, bool):
                raise RuntimeError("External integration enabled must be a boolean")
            entries = metadata.get("clientFiles", [])
            if not isinstance(entries, list):
                raise RuntimeError("External integration clientFiles must be a list")
            for entry in entries:
                if not isinstance(entry, dict):
                    raise RuntimeError("External integration clientFiles entry must be an object")
                relative, expected = entry.get("path"), entry.get("sha256")
                if (not isinstance(relative, str) or not relative or "\\" in relative
                        or "\x00" in relative or re.match(r"^[A-Za-z]:", relative)):
                    raise RuntimeError("External integration path must be a client-relative POSIX path")
                path = PurePosixPath(relative)
                if path.is_absolute() or ".." in path.parts or path.as_posix() != relative or relative == ".":
                    raise RuntimeError("External integration path must be a normalized client-relative path")
                if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
                    raise RuntimeError("External integration sha256 must be lowercase hexadecimal")
                source = active.joinpath(*path.parts)
                if any(active.joinpath(*path.parts[:i]).is_symlink() for i in range(1, len(path.parts) + 1)):
                    raise RuntimeError(f"External integration source must not be symlinked: {relative}")
                if not source.resolve().is_relative_to(active.resolve()):
                    raise RuntimeError(f"External integration source is missing or outside client: {relative}")
                if relative in result and result[relative]["sha256"] != expected:
                    raise RuntimeError(f"Conflicting external integration hashes: {relative}")
                if relative in result and result[relative].get("enabled", True) != enabled:
                    raise RuntimeError(f"Conflicting external integration activation: {relative}")
                if not enabled:
                    if source.exists():
                        raise RuntimeError(f"Disabled external integration source is still present: {relative}")
                    item = result.setdefault(relative, {"path": relative, "sha256": expected,
                                                        "enabled": False, "manifests": []})
                else:
                    if not source.is_file():
                        raise RuntimeError(f"External integration source is missing or outside client: {relative}")
                    blob = read_stable(source)
                    if digest(blob) != expected:
                        raise RuntimeError(f"External integration source hash mismatch: {relative}")
                    item = result.setdefault(relative, {"path": relative, "sha256": expected,
                                                        "bytes": len(blob), "manifests": []})
                reference = "integrations/resourcepacks/" + manifest.name
                if reference not in item["manifests"]:
                    item["manifests"].append(reference)
    return result


def configured_pack_preserved(current_client, active, name, external):
    for folder in ("config/paxi/resourcepacks", "resourcepacks"):
        relative = folder + "/" + name
        if relative in external and external[relative].get("enabled", True) is False:
            raise RuntimeError(f"Disabled external resource pack remains in load order: {name}")
        if (current_client / relative).exists():
            return True
        if relative in external:
            source = active.joinpath(*PurePosixPath(relative).parts)
            if not source.is_file() or digest(read_stable(source)) != external[relative]["sha256"]:
                raise RuntimeError(f"Configured external resource pack hash mismatch: {name}")
            return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--instance", type=Path)
    parser.add_argument("--server-source", type=Path)
    args = parser.parse_args()
    project = args.project.resolve()
    output = args.output.resolve()
    rules_file = project / "AGENTS.md"
    rules = rules_file.read_text() if rules_file.is_file() else ""
    match = re.search(r"当前活动客户端实例为 `([^`]+)`", rules)
    if not match and not args.instance:
        raise RuntimeError("Active client path is absent from AGENTS.md")
    active = args.instance.resolve() if args.instance else Path(match.group(1))
    if not active.is_dir() or active.is_symlink():
        raise RuntimeError("Active client must be a real local directory")
    spec = importlib.util.spec_from_file_location(
        "expedition_publication", Path(__file__).with_name("publication_filter.py")
    )
    publication = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(publication)
    original_skip = publication.skip_reason
    external = external_resource_files(project, active)
    policy_file = project / "local-only/publication-policy.json"
    policy = json.loads(policy_file.read_text()) if policy_file.is_file() else {}
    excluded_paths = set(policy.get("excludePaths", []))
    list_transforms = {row["path"]: row for row in policy.get("jsonListTransforms", [])}

    def skip(relative):
        if relative in excluded_paths:
            return "local export exclusion"
        return original_skip(relative) or production_exclusion(relative)

    publication.skip_reason = skip
    output.mkdir(parents=True, exist_ok=False)
    current = output / "current"
    current.mkdir()
    excluded = []
    sanitized = []
    files = []

    def write_file(scope, relative, blob, source=None):
        if scope == "client" and relative in external:
            if external[relative].get("enabled", True) is False:
                raise RuntimeError(f"Disabled external integration source is still present: {relative}")
            if digest(blob) != external[relative]["sha256"]:
                raise RuntimeError(f"External integration source changed: {relative}")
            excluded.append({"scope": scope, "path": relative,
                             "reason": "verified external resource integration; bytes omitted"})
            return
        if scope == "server":
            shared = current / "client" / relative
            if shared.is_file() and shared.read_bytes() == blob:
                return
        reason = skip(relative)
        if reason:
            excluded.append({"scope": scope, "path": relative, "reason": reason})
            return
        clean, findings = publication.privacy(relative, blob)
        for finding in findings:
            excluded.append({"scope": scope, "path": finding["path"],
                             "reason": finding["reason"]})
        if clean is None:
            return
        if relative in list_transforms:
            transform = list_transforms[relative]
            value = json.loads(clean.decode("utf-8-sig"))
            field = transform["field"]
            removed = set(transform.get("removeValues", []))
            value[field] = [item for item in value[field] if item not in removed]
            clean = encoded(value)
        if clean != blob:
            sanitized.append({"scope": scope, "path": relative,
                              "reason": "local font paths omitted by publication privacy filter"})
        target = current / scope / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(clean)
        if digest(target.read_bytes()) != digest(clean):
            raise RuntimeError(f"Snapshot verification failed: {relative}")
        files.append({"scope": scope, "path": relative, "sha256": digest(clean),
                      "bytes": len(clean)})

    publication.SOURCE = active
    publication.FOLDERS = [name for name in publication.FOLDERS
                           if name not in {"mods", "shaderpacks"}]
    candidates, omissions = publication.discover()
    excluded.extend({"scope": "client", **row} for row in omissions)
    for relative, path in sorted(candidates.items()):
        write_file("client", relative, read_stable(path), path)

    custom_mods = []
    for path in sorted((active / "mods").glob("expedition-*.jar")):
        relative = "mods/" + path.name
        if path.is_symlink():
            excluded.append({"scope": "client", "path": relative, "reason": "symlink"})
            continue
        if skip(relative):
            excluded.append({"scope": "client", "path": relative, "reason": skip(relative)})
            continue
        write_file("client", relative, read_stable(path), path)
        custom_mods.append(path.name)
    for name in PATCHED_DEPENDENCIES:
        path = active / "mods" / name
        if not path.is_file():
            continue
        write_file("client", "mods/" + name, read_stable(path), path)

    server_candidates = (
        Path(__file__).resolve().parents[1] / "current/server",
        project / "clients/cmi-expedition/distribution/repository/current/server",
        project / "current/server",
    )
    published_server = next((path for path in server_candidates if path.is_dir()), None)
    deployment = (args.server_source.resolve() if args.server_source else
                  published_server if published_server else
                  project / "servers/cmi-expedition/deployment")
    publication.SOURCE = deployment
    publication.FOLDERS = ["config", "defaultconfigs", "hotai", "ldlib"]
    candidates, omissions = publication.discover()
    excluded.extend({"scope": "server", **row} for row in omissions)
    for relative, path in sorted(candidates.items()):
        write_file("server", relative, read_stable(path), path)
    for path in sorted(deployment.iterdir()):
        if path.is_file() and path.name not in {"server-patches.json", "server-additions.json"}:
            excluded.append({"scope": "server", "path": path.name,
                             "reason": "host, launcher or runtime root file outside deployment snapshot"})

    patches = json.loads((deployment / "server-patches.json").read_text())
    patch_rows = []
    for row in patches.get("mods", []):
        path = deployment / "mods" / row["file"]
        blob = read_stable(path)
        if digest(blob) != row["patchedSha256"]:
            raise RuntimeError(f"Deployment patch hash mismatch: {row['file']}")
        if len(blob) > 1024 * 1024:
            raise RuntimeError(f"Deployment patch exceeds small-patch budget: {row['file']}")
        write_file("server", "mods/" + path.name, blob, path)
        patch_rows.append({key: row[key] for key in
                           ("file", "patchId", "upstreamSha256", "patchedSha256", "changedZipMembers")
                           if key in row})
    current_patches = {"schemaVersion": patches.get("schemaVersion", 1),
                       "scope": "dedicated-server", "mods": patch_rows,
                       "behaviorChange": patches.get("behaviorChange", ""),
                       "deferredRandomTickMitigationRemainsEnabled":
                       patches.get("deferredRandomTickMitigationRemainsEnabled", False)}
    write_file("server", "server-patches.json", encoded(current_patches))

    additions = json.loads((deployment / "server-additions.json").read_text())
    addition_rows = []
    for row in additions.get("mods", []):
        path = deployment / "server-additions" / row["file"]
        if not path.name.startswith("expedition-") or skip("mods/" + path.name):
            excluded.append({"scope": "server", "path": "server-additions/" + path.name,
                             "reason": "unselected deployment addition"})
            continue
        blob = read_stable(path)
        if digest(blob) != row["sha256"]:
            raise RuntimeError(f"Deployment addition hash mismatch: {row['file']}")
        write_file("server", "server-additions/" + path.name, blob, path)
        addition_rows.append({key: row[key] for key in ("file", "patchId", "sha256", "modIds") if key in row})
    write_file("server", "server-additions.json",
               encoded({"schemaVersion": additions.get("schemaVersion", 1), "mods": addition_rows}))

    verified_urls = {}
    manifest = project / "clients/cmi-expedition/distribution/repository/mods.tsv"
    for row in csv.reader(manifest.read_text().splitlines(), delimiter="\t"):
        if len(row) >= 3 and re.fullmatch(r"[0-9a-f]{64}", row[0]) and public_url(row[2]):
            verified_urls.setdefault(("sha256", row[0]), (row[2], "mods.tsv"))
    for path in sorted((active / "mods/.index").glob("*.toml")):
        record = tomllib.loads(path.read_text())
        download = record.get("download", {})
        algorithm = download.get("hash-format", "").lower().replace("-", "")
        value = download.get("hash", "").lower()
        url = public_url(download.get("url"))
        if algorithm in {"sha1", "sha256", "sha512"} and value and url:
            verified_urls.setdefault((algorithm, value), (url, "mods/.index/" + path.name))

    existing_lock = (published_server.parent / "mods.lock.json" if published_server else
                     Path(__file__).resolve().parents[1] / "current/mods.lock.json")
    if existing_lock.is_file():
        for row in json.loads(existing_lock.read_text()).get("mods", []):
            url = public_url(row.get("downloadUrl"))
            value = row.get("sha256", "")
            if url and re.fullmatch(r"[0-9a-f]{64}", value):
                verified_urls.setdefault(("sha256", value), (url, "current/mods.lock.json"))

    lock_rows = []
    missing_downloads = []
    for path in sorted((active / "mods").glob("*.jar")):
        if path.is_symlink():
            raise RuntimeError(f"Active mod is symlinked: {path.name}")
        actual, size = hashes(path)
        row = {"filename": path.name, "sha256": actual["sha256"],
               "sha1": actual["sha1"], "bytes": size, "downloadUrl": None}
        for algorithm in ("sha256", "sha1", "sha512"):
            verified = verified_urls.get((algorithm, actual[algorithm]))
            if verified:
                row.update({"downloadUrl": verified[0], "downloadUrlSource": verified[1],
                            "downloadHashFormat": algorithm, "downloadHash": actual[algorithm]})
                break
        if row["downloadUrl"] is None:
            missing_downloads.append(path.name)
        artifact = current / "client/mods" / path.name
        if artifact.is_file():
            file_hash = hashlib.sha256(artifact.read_bytes()).hexdigest()
            if file_hash == row["sha256"]:
                row["localArtifact"] = "client/mods/" + path.name
        lock_rows.append(row)
    lock = {"schemaVersion": 1, "minecraft": "1.20.1", "forge": "47.4.10", "mods": lock_rows}
    (current / "mods.lock.json").write_bytes(encoded(lock))
    order_file = current / "client/config/paxi/resourcepack_load_order.json"
    load_order = json.loads(order_file.read_text()).get("loadOrder", []) if order_file.is_file() else []
    for name in load_order:
        if not configured_pack_preserved(current / "client", active, name, external):
            raise RuntimeError(f"Configured resource pack was not preserved: {name}")
    stats = {}
    for scope in ("client", "server"):
        selected = [row for row in files if row["scope"] == scope]
        stats[scope] = {"files": len(selected), "bytes": sum(row["bytes"] for row in selected)}
    report = {"files": files, "summary": stats, "excluded": excluded,
              "sanitized": sanitized, "modCount": len(lock_rows),
              "modsWithVerifiedDownloadUrl": len(lock_rows) - len(missing_downloads),
              "modsWithoutVerifiedDownloadUrl": missing_downloads,
              "clientProductionCustomJars": custom_mods,
              "resourcePackLoadOrder": load_order,
              "externalResourceReferences": list(external.values()),
              "sourceModified": False,
              "serverSource": "reviewed dedicated-server overlay"}
    (output.parent / "snapshot-result.json").write_bytes(encoded(report))
    print(json.dumps({"summary": stats, "modCount": len(lock_rows),
                      "modsWithVerifiedDownloadUrl": len(lock_rows) - len(missing_downloads),
                      "modsWithoutVerifiedDownloadUrl": len(missing_downloads),
                      "excludedCount": len(excluded), "sanitizedCount": len(sanitized),
                      "clientCustomJars": len(custom_mods)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
