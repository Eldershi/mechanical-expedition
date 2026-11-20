#!/usr/bin/env python3
"""Write deterministic jars without relying on newer JDK jar --date support."""
import argparse
from pathlib import Path
import re
import zipfile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("build", type=Path)
parser.add_argument("--neoforge", nargs=2, metavar=("DIRECTORY", "VERSION"),
                    help="also build a launcher for the named sibling NeoForge instance")
args = parser.parse_args()
build = args.build
launchers = [
    ("server-bootstrap.jar", "classes", "ExpeditionBootstrap", ()),
    ("fake-server.jar", "fake-classes", "FakeServer", ()),
]
if args.neoforge:
    directory, version = args.neoforge
    if (not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", directory)
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)):
        parser.error("--neoforge requires a sibling directory name and a numeric NeoForge version")
    launchers.append(("server-neoforge.jar", "classes", "ExpeditionBootstrap", (
        f"Expedition-NeoForge-Directory: {directory}",
        f"Expedition-NeoForge-Version: {version}",
    )))

for name, classes, main, attributes in launchers:
    with zipfile.ZipFile(build / name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as jar:
        manifest = ("Manifest-Version: 1.0", f"Main-Class: {main}", *attributes, "", "")
        entries = [("META-INF/MANIFEST.MF", "\r\n".join(manifest).encode("ascii"))]
        entries.extend((file.relative_to(build / classes).as_posix(), file.read_bytes())
                       for file in sorted((build / classes).rglob("*.class")))
        for path, data in entries:
            entry = zipfile.ZipInfo(path, (2026, 10, 17, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            jar.writestr(entry, data, compresslevel=9)
