#!/usr/bin/env python3
"""Write deterministic jars without relying on newer JDK jar --date support."""
from pathlib import Path
import sys
import zipfile

build = Path(sys.argv[1])
for name, classes, main in (("server-bootstrap.jar", "classes", "ExpeditionBootstrap"),
                            ("fake-server.jar", "fake-classes", "FakeServer")):
    with zipfile.ZipFile(build / name, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as jar:
        entries = [("META-INF/MANIFEST.MF",
                    f"Manifest-Version: 1.0\r\nMain-Class: {main}\r\n\r\n".encode("ascii"))]
        entries.extend((file.relative_to(build / classes).as_posix(), file.read_bytes())
                       for file in sorted((build / classes).rglob("*.class")))
        for path, data in entries:
            entry = zipfile.ZipInfo(path, (2026, 10, 17, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            jar.writestr(entry, data, compresslevel=9)
