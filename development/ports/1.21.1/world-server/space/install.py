#!/usr/bin/env python3
"""Install matching Earth–Moon structures, scripts, tasks and adapter in test instances."""

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from build_structures import build

HERE = Path(__file__).resolve().parent


def install(client, server, java):
    if not (client / "mods/adastra-1.21.1-1.16.26-neoforge.jar").is_file():
        raise ValueError("Client does not match the 1.21.1 space baseline")
    if not (server / "libraries/net/neoforged/neoforge/21.1.267/unix_args.txt").is_file():
        raise ValueError("Server does not match NeoForge 21.1.267")
    if not (server / "mods/adastra-1.21.1-1.16.26-neoforge.jar").is_file():
        raise ValueError("Server does not match the 1.21.1 space baseline")
    with tempfile.TemporaryDirectory() as directory:
        staged = Path(directory)
        overlay = staged / "overlay"
        build(overlay)
        shutil.copytree(HERE / "overlay", overlay, dirs_exist_ok=True)
        subprocess.run([sys.executable, str(HERE.parent / "build.py"), "--java", str(java),
                        "--server", str(server), "--output", str(staged), "space"], check=True)
        adapter, = staged.glob("*.jar")
        with ZipFile(adapter) as archive:
            if b"expedition_space_acceptance" in archive.read("META-INF/neoforge.mods.toml"):
                raise ValueError("Acceptance mod may only be installed in a disposable verification instance")
        for instance in (client, server):
            shutil.copytree(overlay, instance, dirs_exist_ok=True)
            shutil.copy2(adapter, instance / "mods")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    options = parser.parse_args()
    install(options.client.resolve(), options.server.resolve(), options.java.resolve())
