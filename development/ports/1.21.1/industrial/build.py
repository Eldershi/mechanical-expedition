#!/usr/bin/env python3
"""Build the Expedition industrial add-ons against a NeoForge 1.21.1 server."""

import argparse
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent
MODULES = {
    "flight-pneumatics-compat": (),
    "storage-adjustments": ("functionalstorage-", "sophisticatedcore-", "titanium-"),
    "engineering-adjustments": ("immersiveengineering-",),
    "refinery-steam-compat": ("immersiveengineering-", "createcraftedbeginning-"),
}


def build(module, java, server, output):
    launch, = server.glob("libraries/net/neoforged/neoforge/21.1.*/unix_args.txt")
    patched, = launch.parent.glob("*-server.jar")
    universal, = launch.parent.glob("*-universal.jar")
    vanilla, = (server / "libraries/net/minecraft/server").glob("*/*-srg.jar")
    legacy = next(line.removeprefix("-DlegacyClassPath=")
                  for line in launch.read_text().splitlines()
                  if line.startswith("-DlegacyClassPath="))
    addons = []
    for prefix in MODULES[module]:
        addon, = (path for path in (server / "mods").glob("*.jar")
                  if path.name.lower().startswith(prefix))
        addons.append(addon)
    classpath = os.pathsep.join(map(str, (patched, vanilla, universal, *addons,
                                         *(server / path for path in legacy.split(os.pathsep)))))
    source = HERE / module
    sources = sorted((source / "src").rglob("*.java"))
    with TemporaryDirectory() as temp:
        classes = Path(temp)
        subprocess.run([str(java), "-m", "jdk.compiler/com.sun.tools.javac.Main",
                        "--release", "21", "-proc:none", "-encoding", "UTF-8",
                        "-cp", classpath, "-d", str(classes), *map(str, sources)], check=True)
        output.mkdir(parents=True, exist_ok=True)
        target = output / f"expedition-{module}-neoforge-1.0.0.jar"
        with ZipFile(target, "w", compression=ZIP_DEFLATED) as jar:
            for directory in (classes, source / "resources"):
                for file in sorted(path for path in directory.rglob("*") if path.is_file()):
                    name = file.relative_to(directory).as_posix()
                    jar.writestr(ZipInfo(name), file.read_bytes(), compress_type=ZIP_DEFLATED)
    print(target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", choices=MODULES)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    options = parser.parse_args()
    build(options.module, options.java, options.server.resolve(), options.output)
