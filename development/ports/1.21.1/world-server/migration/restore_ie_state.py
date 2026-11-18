#!/usr/bin/env python3
"""Restore legacy IE item data in matched workbenches, cloches, and audited Create vault slots."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import nbtlib

from measure_chunk_edges import read_chunk
from prepare_region_copy import SECTOR, replace_chunk


WORKBENCH = "immersiveengineering:modworkbench"
CLOCHE = "immersiveengineering:cloche_master"
VAULT = "create:item_vault"
BLUEPRINT = "immersiveengineering:blueprint"


def items(entity):
    holder = entity.get("Inventory", {}) if entity["id"] == VAULT else entity
    return holder.get("Items")


def containers(chunk, include_vaults):
    types = {WORKBENCH, CLOCHE, VAULT} if include_vaults else {WORKBENCH, CLOCHE}
    return {tuple(int(entity[key]) for key in "xyz"): entity
            for entity in chunk.get("block_entities", ()) if entity.get("id") in types}


def eligible_recovery(recovery):
    entries = {}
    for item in recovery.get("Stacks", ()):
        stack = item.get("OriginalStack", {})
        tag = stack.get("tag", {})
        if (item.get("BlockEntity") != VAULT or item.get("Reason") != "unverified_mod_payload"
                or stack.get("id") != BLUEPRINT or set(tag) != {"blueprint"} or "Slot" not in stack):
            continue
        key = (tuple(map(int, item["BlockPos"])), int(stack["Slot"]))
        if key in entries:
            raise ValueError(f"Duplicate blueprint recovery entry at {key}")
        entries[key] = item
    return entries


def restore_cloche(position, original, stack, report):
    if stack is None or stack.get("id") != original.get("id") or original.get("tag") or stack.get("components"):
        return False
    previous = int(original.get("Count", 0))
    current = int(stack.get("count", 0))
    if not (current == 1 and 1 < previous <= 64):
        return False
    stack["count"] = nbtlib.Int(previous)
    report["cloche_counts"].append({"position": position, "slot": int(original["Slot"]),
                                    "item": str(original["id"]), "before": current, "after": previous})
    return True


def restore_chunk(originals, new, report, recovered, completed):
    retained = containers(new, bool(recovered))
    changed = False
    for position, source in originals.items():
        target = retained.get(position)
        if target is None or target.get("id") != source["id"]:
            continue
        target_items = items(target)
        current = {int(stack["Slot"]): stack for stack in target_items or ()}
        for original in items(source) or ():
            slot = int(original["Slot"])
            stack = current.get(slot)
            if source["id"] == CLOCHE:
                changed |= restore_cloche(position, original, stack, report)
                continue
            category = original.get("tag", {}).get("blueprint")
            if original.get("id") != BLUEPRINT or not isinstance(category, nbtlib.String) or not category:
                continue
            key = (position, slot)
            recovery_entry = recovered.get(key)
            if source["id"] == VAULT and (recovery_entry is None or recovery_entry["OriginalStack"] != original):
                continue
            details = {"position": position, "owner": str(source["id"]), "slot": slot, "category": str(category)}
            count = int(original.get("Count", 1))
            if stack is None and recovery_entry is not None and target_items is not None and (
                    0 <= slot < int(target["Inventory"]["Size"]) and 0 < count <= 64):
                target_items.append(nbtlib.Compound({
                    "id": nbtlib.String(BLUEPRINT), "count": nbtlib.Int(count), "Slot": nbtlib.Int(slot),
                    "components": nbtlib.Compound({BLUEPRINT: category}),
                }))
                report["restored"].append(dict(details, stack_recovered=True))
                completed.add(key)
                changed = True
                continue
            if (stack is None or stack.get("id") != BLUEPRINT
                    or int(stack.get("count", 1)) != count):
                report["unmatched"].append(details)
                continue
            components = stack.setdefault("components", nbtlib.Compound())
            if BLUEPRINT not in components:
                components[BLUEPRINT] = category
                report["restored"].append(details)
                if recovery_entry is not None:
                    completed.add(key)
                changed = True
            elif components[BLUEPRINT] == category:
                report["already_valid"] += 1
                if recovery_entry is not None:
                    completed.add(key)
            else:
                report["conflicts"].append(dict(details, target_category=str(components[BLUEPRINT])))
    return changed


def occupied(path):
    with path.open("rb") as file:
        header = file.read(SECTOR)
    if len(header) != SECTOR:
        raise ValueError(f"Short region header in {path.name}")
    return {slot for slot in range(1024) if int.from_bytes(header[slot * 4:slot * 4 + 3], "big")}


def migrate(source, target, output, recovery):
    report = {"restored": [], "cloche_counts": [], "conflicts": [], "unmatched": [],
              "already_valid": 0, "regions": []}
    recovered = eligible_recovery(recovery)
    completed = set()
    for target_file in sorted(target.glob("r.*.mca")):
        source_file = source / target_file.name
        if not source_file.exists():
            continue
        rx, rz = map(int, target_file.name.split(".")[1:3])
        region = None
        for slot in sorted(occupied(source_file) & occupied(target_file)):
            cx, cz = rx * 32 + slot % 32, rz * 32 + slot // 32
            old = read_chunk(source, cx, cz)
            if old is None:
                continue
            originals = containers(old, bool(recovered))
            if not any(entity.get("id") == CLOCHE or any(stack.get("id") == BLUEPRINT for stack in items(entity) or ())
                       for entity in originals.values()):
                continue
            new = read_chunk(target, cx, cz)
            if new is None or int(new.get("DataVersion", 0)) != 3955:
                continue
            if not restore_chunk(originals, new, report, recovered, completed):
                continue
            if region is None:
                region = bytearray(target_file.read_bytes())
            offset = int.from_bytes(region[slot * 4:slot * 4 + 3], "big") * SECTOR
            if region[offset + 4] & 128:
                raise ValueError(f"External chunk storage is unsupported for {(cx, cz)}")
            replace_chunk(region, slot * 4, offset, region[slot * 4 + 3], new)
        if region is not None:
            (output / target_file.name).write_bytes(region)
            report["regions"].append(target_file.name)
    if "Stacks" in recovery:
        removed = {id(recovered[key]) for key in completed}
        recovery["Stacks"] = nbtlib.List[nbtlib.Compound](
            item for item in recovery["Stacks"] if id(item) not in removed
        )
        recovery.save(output / "unconverted-stacks.nbt", gzipped=True)
    report["vault_recovery_entries_completed"] = len(completed)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-regions", required=True, type=Path)
    parser.add_argument("--target-regions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path, help="New directory for changed region files and the report")
    parser.add_argument("--vault-recovery", type=Path, help="Create inventory recovery NBT for audited missing items")
    args = parser.parse_args()
    source, target, output = (path.resolve() for path in (args.source_regions, args.target_regions, args.output))
    if (source == target or not source.is_dir() or not target.is_dir() or output.exists()
            or source in output.parents or target in output.parents):
        parser.error("Use separate source and target directories and a new output outside both")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="ie-blueprint-", dir=output.parent) as temp:
        stage = Path(temp) / "regions"
        stage.mkdir()
        recovery = nbtlib.load(args.vault_recovery) if args.vault_recovery else nbtlib.File()
        report = migrate(source, target, stage, recovery)
        (stage / "ie-state-report.json").write_text(json.dumps(report, indent=2) + "\n")
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    print(json.dumps({key: len(value) if isinstance(value, list) else value
                      for key, value in report.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
