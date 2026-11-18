#!/usr/bin/env python3
"""Compile the NeoForge server adapter and run the existing command regression."""

import argparse
import json
import os
from pathlib import Path
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent


def compile_adapter(java, server, ftb, shared):
    launch_args, = server.glob("libraries/net/neoforged/neoforge/21.1.*/unix_args.txt")
    legacy = next(line.removeprefix("-DlegacyClassPath=")
                  for line in launch_args.read_text().splitlines()
                  if line.startswith("-DlegacyClassPath="))
    patched, = launch_args.parent.glob("*-server.jar")
    universal, = launch_args.parent.glob("*-universal.jar")
    vanilla, = (server / "libraries/net/minecraft/server").glob("*/*-srg.jar")
    paths = [patched, vanilla, universal, *(server / path for path in legacy.split(os.pathsep))]
    classes = HERE / "build/classes"
    classes.mkdir(parents=True, exist_ok=True)
    classpath = os.pathsep.join(map(str, paths))
    subprocess.run([
        str(java), "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "21",
        "-proc:none", "-encoding", "UTF-8", "-cp", classpath, "-d", str(classes),
        str(HERE / "FtbActionAnnouncements.java"),
        str(shared / "src/expedition/ftb/SuccessfulFtbAction.java"),
        str(shared / "tests/ActionRegression.java"),
    ], check=True)
    subprocess.run([
        str(java), "-Xverify:all", "-cp", str(classes) + os.pathsep + classpath, "ActionRegression",
    ], check=True)
    with ZipFile(ftb) as jar:
        for action in ("gamemode", "rain", "day", "night"):
            button = json.loads(jar.read(f"assets/ftblibrary/sidebar_buttons/toggle/{action}.json"))
            if button.get("click") != [f"command:/ftblibrary {action}"] or not button.get("requires_op"):
                raise ValueError(f"Unexpected FTB sidebar action: {action}")
    jar = HERE / "build/expedition-ftb-action-announcements-neoforge-1.0.0.jar"
    inputs = [
        ("META-INF/neoforge.mods.toml", HERE / "neoforge.mods.toml"),
        *((path.relative_to(classes).as_posix(), path)
          for path in sorted((classes / "expedition").rglob("*.class"))),
    ]
    with ZipFile(jar, "w") as archive:
        for name, path in inputs:
            info = ZipInfo(name)
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, path.read_bytes())
    print(jar)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--ftb", type=Path, required=True)
    parser.add_argument("--shared", type=Path, default=HERE.parent)
    options = parser.parse_args()
    compile_adapter(options.java, options.server, options.ftb, options.shared)
