#!/usr/bin/env python3
"""Build the selected creeper adapter against the pinned test server."""

import argparse
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent


def build(java, server, output):
    launch_args, = server.glob("libraries/net/neoforged/neoforge/21.1.*/unix_args.txt")
    legacy_classpath = next(line.split("=", 1)[1] for line in launch_args.read_text().splitlines()
                            if line.startswith("-DlegacyClassPath="))
    patched, = launch_args.parent.glob("*-server.jar")
    universal, = launch_args.parent.glob("*-universal.jar")
    vanilla, = server.glob("libraries/net/minecraft/server/*/*-srg.jar")
    firework, = server.glob("mods/CreeperFirework-neoforge-2.2.0.jar")
    classpath = [patched, vanilla, universal, firework, *(server / p for p in legacy_classpath.split(os.pathsep))]
    with TemporaryDirectory() as tmp:
        classes = Path(tmp)
        subprocess.run([
            java, "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "21",
            "-proc:none", "-encoding", "UTF-8", "-cp", os.pathsep.join(map(str, classpath)),
            "-d", classes, *sorted((HERE / "src").rglob("*.java")),
        ], check=True)
        entries = [
            ("META-INF/neoforge.mods.toml", HERE / "neoforge.mods.toml"),
            ("expedition-creeper-firework.mixins.json", HERE / "expedition-creeper-firework.mixins.json"),
            *((name.relative_to(classes).as_posix(), name) for name in sorted(classes.rglob("*.class"))),
        ]
        output.parent.mkdir(parents=True, exist_ok=True)
        with ZipFile(output, "w") as jar:
            for name, source in entries:
                info = ZipInfo(name)
                info.compress_type = ZIP_DEFLATED
                jar.writestr(info, source.read_bytes())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", required=True, type=Path)
    parser.add_argument("--server", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    build(args.java, args.server, args.output)
