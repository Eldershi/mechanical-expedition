#!/usr/bin/env python3
"""Stage reviewed Anvil records over a current server snapshot."""

import argparse
from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path


SECTOR = 4096
HEADER = 2 * SECTOR
LAYERS = ("region", "entities", "poi")


@dataclass(frozen=True)
class Record:
    data: bytes
    timestamp: bytes


def records(data):
    if not data:
        return {}
    if len(data) < HEADER:
        raise ValueError("Truncated Anvil header")
    result = {}
    occupied = {0, 1}
    for slot in range(1024):
        entry = slot * 4
        offset = int.from_bytes(data[entry:entry + 3], "big")
        capacity = data[entry + 3]
        if not offset and not capacity:
            continue
        start = offset * SECTOR
        limit = start + capacity * SECTOR
        length = int.from_bytes(data[start:start + 4], "big")
        sectors = set(range(offset, offset + capacity))
        if (not capacity or sectors & occupied
                or not 1 <= length <= min(limit, len(data)) - start - 4):
            raise ValueError(f"Invalid Anvil record at slot {slot}")
        occupied.update(sectors)
        result[slot] = Record(data[start:start + 4 + length],
                              data[entry + SECTOR:entry + SECTOR + 4])
    return result


def image(records_by_slot):
    result = bytearray(HEADER)
    for slot, record in sorted(records_by_slot.items()):
        offset = len(result) // SECTOR
        sectors = (len(record.data) + SECTOR - 1) // SECTOR
        entry = slot * 4
        result[entry:entry + 4] = offset.to_bytes(3, "big") + bytes([sectors])
        result[entry + SECTOR:entry + SECTOR + 4] = record.timestamp
        result.extend(record.data)
        result.extend(bytes(sectors * SECTOR - len(record.data)))
    return bytes(result)


def read(path):
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return b""


def protected_plan(plan):
    protected = {tuple(pair) for pair in plan.get("protected", [])}
    regions = defaultdict(set)
    planned = plan["layers"]
    if set(planned) != set(LAYERS):
        raise ValueError(f"Expected explicit chunk lists for {', '.join(LAYERS)}")
    terrain = {tuple(pair) for pair in planned["region"]}
    for layer in LAYERS:
        for x, z in {tuple(pair) for pair in planned[layer]}:
            if (x, z) in protected:
                raise ValueError(f"Protected chunk ({x}, {z}) in {layer} overlay")
            if (x, z) not in terrain:
                raise ValueError(f"Auxiliary overlay outside terrain scope at ({x}, {z})")
            regions[layer, x // 32, z // 32].add((x % 32) + (z % 32) * 32)
    return regions


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stage(current, reviewed, output, plan):
    targets = protected_plan(plan)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    manifest = {}
    for (layer, rx, rz), slots in sorted(targets.items()):
        relative = Path(layer) / f"r.{rx}.{rz}.mca"
        before = read(current / relative)
        baseline = records(before)
        donor = records(read(reviewed / relative))
        merged = baseline.copy()
        for slot in slots:
            source = baseline.get(slot)
            supplied = donor.get(slot)
            if any(record and record.data[4] & 128 for record in (source, supplied)):
                raise ValueError(f"External Anvil record requires a sidecar-aware merge: {relative}, {slot}")
            if supplied is None:
                if layer == "region":
                    raise ValueError(f"No reviewed terrain: {relative}, {slot}")
                merged.pop(slot, None)
            else:
                merged[slot] = supplied
        if merged == baseline:
            continue
        after = image(merged)
        staged = output / relative
        staged.parent.mkdir(exist_ok=True)
        staged.write_bytes(after)
        reread = records(staged.read_bytes())
        if reread != merged or any(reread.get(slot) != baseline.get(slot)
                                  for slot in baseline.keys() - slots):
            raise ValueError(f"Anvil read-back did not preserve unlisted records: {relative}")
        manifest[str(relative)] = {"current_sha256": digest(before) if (current / relative).exists() else None,
                                   "staged_sha256": digest(after),
                                   "changed_chunks": sum(merged.get(i) != baseline.get(i) for i in slots)}
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("current", "reviewed", "output", "plan", "manifest"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    manifest = stage(args.current, args.reviewed, args.output, plan)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    counts = {layer: sum(row["changed_chunks"] for path, row in manifest.items()
                         if path.startswith(f"{layer}/")) for layer in LAYERS}
    print(f"Staged {len(manifest)} region files, with changed records by layer {counts}")


if __name__ == "__main__":
    main()
