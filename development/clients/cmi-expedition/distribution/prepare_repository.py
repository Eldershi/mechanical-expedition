"""Synchronize generated release source into the local publishing checkout."""

import json
from pathlib import Path
import shutil
import subprocess


HERE = Path(__file__).resolve().parent
config = json.loads((HERE / "config.json").read_text())
source = HERE / "dist" / config["version"] / "repository"
target = HERE / "repository"
rules = HERE.parents[2] / "AGENTS.md"
maintained_prefixes = ("current/", "development/")
maintained_files = {"AGENTS.md", "README.md", "tools/snapshot_current.py", "tools/publication_filter.py"}
assert (source / "release.env").is_file()
assert json.loads((source.parent / "audit.json").read_text())["passed"]
assert rules.is_file()
if (target / ".git").exists():
    status = subprocess.check_output(["git", "-C", str(target), "status", "--porcelain"], text=True)
    if status.strip():
        raise SystemExit("Publishing checkout has uncommitted changes; preserve them before regenerating.")
    old = subprocess.check_output(["git", "-C", str(target), "ls-files", "-z"]).decode().split("\0")
    new = {path.relative_to(source).as_posix() for path in source.rglob("*") if path.is_file()} | {"AGENTS.md"}
    for relative in old:
        if relative and relative not in new and relative not in maintained_files and not relative.startswith(maintained_prefixes):
            (target / relative).unlink()
elif target.exists() and any(target.iterdir()):
    raise SystemExit("Refusing to overwrite an unrelated directory")
target.mkdir(parents=True, exist_ok=True)
for entry in source.iterdir():
    destination = target / entry.name
    if entry.name == "README.md" and destination.is_file():
        shutil.copy2(entry, target / "RELEASE-GUIDE.md")
    elif entry.is_dir():
        shutil.copytree(entry, destination, dirs_exist_ok=True)
    else:
        shutil.copy2(entry, destination)
shutil.copy2(rules, target / "AGENTS.md")
if not (target / ".git").exists():
    subprocess.run(["git", "init", "-q", "-b", "main", str(target)], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.name", "Eldershi"], check=True)
    subprocess.run(["git", "-C", str(target), "config", "user.email", "127774053+Eldershi@users.noreply.github.com"], check=True)
subprocess.run(["git", "-C", str(target), "add", "."], check=True)
print(target)
