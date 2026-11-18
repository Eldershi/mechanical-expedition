#!/usr/bin/env python3
"""Convert legacy FTB quest filters using the target pack's own SNBT parser."""

import argparse
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java", required=True, type=Path)
    parser.add_argument("--server", required=True, type=Path)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    library = args.server / "libraries"
    launch_args, = library.glob("net/neoforged/neoforge/21.1.*/unix_args.txt")
    legacy_classpath = next(line.split("=", 1)[1] for line in launch_args.read_text().splitlines()
                            if line.startswith("-DlegacyClassPath="))
    patched, = launch_args.parent.glob("*-server.jar")
    vanilla, = library.glob("net/minecraft/server/*/*-srg.jar")
    ftb, = (args.server / "mods").glob("ftb-library-neoforge-*.jar")
    paths = [patched, vanilla, ftb, *(args.server / jar for jar in legacy_classpath.split(os.pathsep))]
    subprocess.run([
        args.java, "--class-path", os.pathsep.join(map(str, paths)),
        Path(__file__).with_name("ConvertItemFilters.java"), args.source, args.output,
    ], check=True)


if __name__ == "__main__":
    main()
