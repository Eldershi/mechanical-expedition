#!/usr/bin/env python3
"""Update a stopped NeoForge profile from the verified release checkout."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory

import package_test as release
import production_overlay as production


ROOT = release.ROOT
CLIENT = ROOT / "current/client"
LOCK = "current/mods.lock.json"
STAMP = Path(".expedition-release.json")
PAXI = production.PAXI_ORDER.as_posix()


def digest(path, algorithm="sha256"):
    if not path.is_file():
        return None
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def instance_file(profile, name):
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Invalid profile path: {name}")
    path = profile / relative
    for part in (path, *path.parents):
        if part == profile:
            break
        if part.is_symlink():
            raise ValueError(f"Symbolic link in profile path: {name}")
    if path.exists() and not path.is_file():
        raise ValueError(f"Expected a regular profile file: {name}")
    return path


def stage_file(work, name, expected, sources, url=None):
    target = work / name
    for source in sources:
        if digest(source) == expected:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            break
    else:
        if not url:
            raise ValueError(f"No source with the locked hash for {name}")
        production.fetch_verified(target, url, expected)
    if digest(target) != expected:
        raise ValueError(f"Staged hash mismatch for {name}")


def stage_paxi(target, existing, old_revision, expected):
    order = release.json_file(CLIENT / PAXI)
    production.enable_thermal_style(order)
    payload = (json.dumps(order, indent=2) + "\n").encode()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError("The resource-pack order differs from the client lock")
    if existing.is_file():
        local = release.json_file(existing)
        previous = json.loads(release.git("show", f"{old_revision}:current/client/{PAXI}"))
        managed = set(previous["loadOrder"]) | set(order["loadOrder"])
        configured = local["loadOrder"]
        if [name for name in configured if name in managed] == order["loadOrder"]:
            return False
        local["loadOrder"] = order["loadOrder"] + [name for name in configured if name not in managed]
        payload = (json.dumps(local, ensure_ascii=False, indent=2) + "\n").encode()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return True


def plan(profile, before, target, previous_revision, work, preserved):
    updates = {}
    overlay = {path.as_posix(): source for path, source in production.files(True).items()}
    old_files = before["files"]
    new_files = target["files"]
    for name in sorted(old_files.keys() | new_files.keys()):
        if name in preserved:
            continue
        old, expected = old_files.get(name), new_files.get(name)
        if old == expected and name not in overlay:
            continue
        path = instance_file(profile, name)
        if name == PAXI and expected:
            if stage_paxi(work / name, path, previous_revision, expected):
                updates[name] = digest(path)
            continue
        actual = digest(path)
        if actual == expected:
            continue
        if actual is not None and actual != old:
            raise ValueError(f"Locally modified managed file: {name}. Reconcile it or explicitly preserve it.")
        if expected:
            stage_file(work, name, expected, [overlay.get(name, CLIENT / name)])
        updates[name] = actual

    old_mods = {row["filename"]: row for row in before["mods"]}
    new_mods = {row["filename"]: row for row in target["mods"]}
    for filename in sorted(old_mods.keys() | new_mods.keys()):
        if Path(filename).name != filename or not filename.endswith(".jar"):
            raise ValueError(f"Invalid locked mod filename: {filename}")
        name = f"mods/{filename}"
        path = instance_file(profile, name)
        actual = digest(path)
        row = new_mods.get(filename)
        if row is None:
            if actual is None:
                continue
            if actual != old_mods[filename]["sha256"]:
                raise ValueError(f"Locally modified retired mod: {name}")
        else:
            if actual == row["sha256"] and path.stat().st_size == row["bytes"]:
                continue
            if actual is not None and actual != old_mods.get(filename, {}).get("sha256"):
                raise ValueError(f"Locally modified mod: {name}")
            stage_file(work, name, row["sha256"], [CLIENT / name], row.get("downloadUrl"))
            if (work / name).stat().st_size != row["bytes"]:
                raise ValueError(f"Staged size mismatch for {name}")
        updates[name] = actual
    return updates


def plan_resources(profile, previous_revision, work, preserved, updates):
    previous = json.loads(release.git("show", f"{previous_revision}:modrinth.index.json"))
    before = {row["path"]: row["hashes"]["sha512"] for row in previous["files"]
              if not row["path"].startswith("mods/")}
    resources = {row["path"]: row for row in release.external_client_resources()}
    for name in sorted(before.keys() | resources.keys()):
        if name in preserved:
            continue
        path = instance_file(profile, name)
        row = resources.get(name)
        actual = digest(path)
        expected = row["sha256"] if row else None
        if actual == expected:
            continue
        if actual is not None and (
            name not in before or digest(path, "sha512") != before[name]
        ):
            raise ValueError(f"Locally modified resource pack or shader: {name}. Use --preserve to retain it.")
        if row:
            stage_file(work, name, expected, [CLIENT / name], row["downloadUrl"])
        updates[name] = actual


def assert_stopped(profile):
    processes = subprocess.check_output(["ps", "-axo", "comm,args"], text=True)
    for line in processes.splitlines()[1:]:
        if line.strip() and Path(line.split()[0]).name == "java" and str(profile) in line:
            raise ValueError("Close the Minecraft instance before applying the update")


def install(profile, work, backup, updates):
    completed = {}
    try:
        for name, original in updates.items():
            path = instance_file(profile, name)
            if digest(path) != original:
                raise ValueError(f"Profile changed during preparation: {name}")
            saved = backup / name
            if original:
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, saved)
            completed[name] = original
            replacement = work / name
            if replacement.is_file():
                path.parent.mkdir(parents=True, exist_ok=True)
                expected = digest(replacement)
                replacement.replace(path)
                if digest(path) != expected:
                    raise ValueError(f"Installed hash mismatch for {name}")
            else:
                path.unlink()
    except BaseException:
        for name, original in reversed(completed.items()):
            path = profile / name
            if original:
                (backup / name).replace(path)
            else:
                path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--from-ref", help="Previously installed commit or tag on the first run")
    parser.add_argument("--preserve", action="append", default=[], help="Keep a specific personal profile setting")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    profile = args.profile.resolve(strict=True)
    if not (profile / "mods").is_dir():
        parser.error("Supply an existing Minecraft profile with a mods directory")
    if release.git("status", "--porcelain"):
        raise ValueError("Commit the release changes before synchronizing the profile")
    subprocess.run([sys.executable, str(Path(release.__file__)), "validate"], check=True)
    revision = release.git("rev-parse", "HEAD")
    receipt = instance_file(profile, STAMP.as_posix())
    previous = release.json_file(receipt)["commit"] if receipt.is_file() else args.from_ref
    if not previous:
        parser.error("Use --from-ref for a profile with no installed commit yet")
    previous = release.git("rev-parse", "--verify", "--end-of-options", f"{previous}^{{commit}}")
    subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", previous, revision], check=True)
    before = json.loads(release.git("show", f"{previous}:{LOCK}"))["client"]
    target = release.json_file(ROOT / LOCK)["client"]
    preserved = {"options.txt", *args.preserve}
    if args.apply:
        assert_stopped(profile)
    with TemporaryDirectory(prefix=".expedition-update-", dir=profile if args.apply else None) as directory:
        directory = Path(directory)
        work = directory / "staged"
        updates = plan(profile, before, target, previous, work, preserved)
        plan_resources(profile, previous, work, preserved, updates)
        writes = sum((work / name).is_file() for name in updates)
        print(f"{revision}: {writes} updates, {len(updates) - writes} removals")
        for name in updates:
            print(("update " if (work / name).is_file() else "remove ") + name)
        if args.apply:
            assert_stopped(profile)
            work.mkdir(exist_ok=True)
            release.write_json(work / STAMP, {"commit": revision})
            updates[STAMP.as_posix()] = digest(receipt)
            install(profile, work, directory / "backup", updates)
            print(f"Verified installed commit {revision}")


if __name__ == "__main__":
    main()
