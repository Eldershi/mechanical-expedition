#!/usr/bin/env python3
"""Install only the reviewed parallel-recipe catalog into the active client."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path


RELEASE = Path(__file__).resolve().parent
CATALOG_REL = Path("kubejs/config/expedition-selected-native-recipes.json")
ACTIVE_CLIENT = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    manifest = json.loads((RELEASE / "manifest.json").read_bytes())
    expected_old = manifest["oldCatalogSha256"]
    expected_new = manifest["newCatalogSha256"]
    source = RELEASE / "payload" / CATALOG_REL
    destination = ACTIVE_CLIENT / CATALOG_REL
    backup = RELEASE / "backups/active-client-before" / CATALOG_REL
    payload = source.read_bytes()
    assert sha256(payload) == expected_new, "Payload hash does not match reviewed manifest"
    before = destination.read_bytes()
    before_sha = sha256(before)
    assert before_sha in (expected_old, expected_new), "Active client catalog changed; refusing overwrite"

    if backup.exists():
        assert sha256(backup.read_bytes()) == expected_old, "Existing active-client backup is unexpected"
    else:
        backup_bytes = before
        if before_sha == expected_new:
            backup_bytes = (
                RELEASE / "backups/project-before/servers/cmi-expedition/instance" / CATALOG_REL
            ).read_bytes()
        assert sha256(backup_bytes) == expected_old
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(backup_bytes)

    changed = before_sha != expected_new
    if changed:
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=destination.parent,
                prefix=".netherite-recipe-restore-", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temp_path, stat.S_IMODE(destination.stat().st_mode))
            os.replace(temp_path, destination)
            temp_path = None
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    after_sha = sha256(destination.read_bytes())
    assert after_sha == expected_new
    receipt = {
        "appliedAtUtc": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "destination": str(destination),
        "backup": str(backup),
        "beforeSha256": before_sha,
        "afterSha256": after_sha,
        "changed": changed,
        "atomicReplace": changed,
        "verified": True,
        "activeClientFilesInstalled": [str(CATALOG_REL)],
    }
    receipt_path = RELEASE / "active-client-install-receipt.json"
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"receipt": str(receipt_path), **receipt}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
