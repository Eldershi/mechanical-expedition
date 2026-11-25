#!/usr/bin/env python3
"""Stage a selective Overworld chunk reset from a stopped server snapshot."""

import argparse
import json
from pathlib import Path
import tarfile

from stage_region_overlay import LAYERS, digest, image, protected_plan, records


def stage_reset(current, output, plan):
    requested = plan["targets"]
    if not requested:
        raise ValueError("No chunks selected for reset")
    regions = protected_plan({
        "protected": plan["protected"],
        "layers": {layer: requested for layer in LAYERS},
    })
    output.mkdir(parents=True, exist_ok=False)
    rollback = output / "rollback"
    replacement = output / "replacement"
    manifest = {}
    for (layer, rx, rz), slots in sorted(regions.items()):
        relative = Path(layer) / f"r.{rx}.{rz}.mca"
        before = (current / relative).read_bytes()
        original = records(before)
        removed = original.keys() & slots
        if not removed:
            continue
        if any(row.data[4] & 128 for row in original.values()):
            raise ValueError(f"Anvil sidecars require separate handling: {relative}")
        retained = {slot: row for slot, row in original.items() if slot not in removed}
        after = image(retained)
        if records(after) != retained:
            raise ValueError(f"Region round trip changed a retained record: {relative}")
        for directory, data in ((rollback, before), (replacement, after)):
            path = directory / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        manifest[relative.as_posix()] = {
            "before": digest(before),
            "after": digest(after),
            "removed": len(removed),
            "preserved": len(retained),
        }
    archive = output / "expedition-overworld-native-reset.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=4) as tar:
        for relative in manifest:
            tar.add(replacement / relative, arcname=relative)
    with tarfile.open(archive, "r:gz") as tar:
        actual = {name: digest(tar.extractfile(name).read()) for name in tar.getnames()}
    if actual != {name: entry["after"] for name, entry in manifest.items()}:
        raise ValueError("Archive checksum mismatch")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("current", "plan", "output"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    manifest = stage_reset(args.current, args.output, plan)
    counts = {layer: sum(entry["removed"] for name, entry in manifest.items()
                         if name.startswith(f"{layer}/")) for layer in LAYERS}
    print(f"Staged {len(manifest)} region files, with removed records by layer {counts}")


if __name__ == "__main__":
    main()
