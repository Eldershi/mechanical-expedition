"""Synchronize publishable release files into the local publishing checkout."""

import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess


def internal_file(relative):
    path = PurePosixPath(relative)
    name = path.name.casefold()
    if any(part.casefold() in {".git", ".agents", ".codex"} for part in path.parts):
        return True
    if name == "agents.md" or (name.startswith("agents ") and name.endswith(".md")):
        return True
    return name.startswith("install_for_codex") or "安装提示词" in name


HERE = Path(__file__).resolve().parent
config = json.loads((HERE / "config.json").read_text())
source = HERE / "dist" / config["version"] / "repository"
target = HERE / "repository"
maintained_prefixes = ("current/", "development/", "integrations/")
maintained_files = {"README.md", "tools/snapshot_current.py", "tools/publication_filter.py"}
assert (source / "release.env").is_file()
assert json.loads((source.parent / "audit.json").read_text())["passed"]
source_files = {
    path.relative_to(source).as_posix(): path
    for path in source.rglob("*")
    if path.is_file() and not path.is_symlink() and not internal_file(path.relative_to(source).as_posix())
}
old = set()
if (target / ".git").exists():
    status = subprocess.check_output(["git", "-C", str(target), "status", "--porcelain"], text=True)
    if status.strip():
        raise SystemExit("Publishing checkout has uncommitted changes; preserve them before regenerating.")
    old = set(filter(None, subprocess.check_output(["git", "-C", str(target), "ls-files", "-z"]).decode().split("\0")))
    for relative in old:
        if internal_file(relative):
            continue
        if relative not in source_files and relative not in maintained_files and not relative.startswith(maintained_prefixes):
            (target / relative).unlink(missing_ok=True)
elif target.exists() and any(target.iterdir()):
    raise SystemExit("Refusing to overwrite an unrelated directory")
target.mkdir(parents=True, exist_ok=True)
copied = set()
for relative, path in source_files.items():
    if relative == "README.md" and (target / "README.md").is_file():
        relative = "RELEASE-GUIDE.md"
    destination = target / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, destination)
    copied.add(relative)
if not (target / ".git").exists():
    subprocess.run(["git", "init", "-q", "-b", "main", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "Eldershi"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "127774053+Eldershi@users.noreply.github.com"], check=True)
excluded = sorted(relative for relative in old if internal_file(relative))
if excluded:
    subprocess.run(["git", "-C", str(target), "--literal-pathspecs", "rm", "--cached", "--ignore-unmatch", "--", *excluded], check=True)
stage = sorted((old | copied) - set(excluded))
if stage:
    subprocess.run(
        ["git", "-C", str(target), "--literal-pathspecs", "add", "--all", "--pathspec-from-file=-", "--pathspec-file-nul"],
        input="".join(relative + "\0" for relative in stage).encode(),
        check=True,
    )
print(target)
