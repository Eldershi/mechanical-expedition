#!/usr/bin/env python3
"""Repair old stack formats and verified Create vault count resets on a closed copy."""

import argparse
from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import nbtlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "migration"))
from audit_block_palettes import region_chunks, terrain_regions
from prepare_region_copy import replace_chunk

VAULT = "create:item_vault"
LEGACY_PLAIN = {"id", "Slot", "Count"}
MODERN_PLAIN = {"id", "Slot", "count"}


def vault_chunks(world):
    for dimension, path in terrain_regions(world):
        data = path.read_bytes()
        for slot, offset, (cx, cz), payload in region_chunks(path, data):
            if VAULT.encode() not in payload:
                continue
            chunk = nbtlib.File.parse(io.BytesIO(payload))
            vaults = [entity for entity in chunk.get("block_entities", ()) if entity.get("id") == VAULT]
            if vaults:
                yield dimension, path, data, slot, offset, (cx, cz), chunk, vaults


def position(entity):
    return tuple(int(entity[axis]) for axis in "xyz")


def vault_items(entity):
    return entity.get("Inventory", {}).get("Items", ())


def stack_count(stack):
    return int(stack.get("count", stack.get("Count", 0)))


def read_stacks(world):
    stacks = {}
    for dimension, _, _, _, _, _, _, vaults in vault_chunks(world):
        for entity in vaults:
            xyz = position(entity)
            for stack in vault_items(entity):
                key = (dimension, *xyz, int(stack["Slot"]))
                if key in stacks or stack_count(stack) <= 0:
                    raise ValueError(f"Invalid vault stack at {key}")
                stacks[key] = stack
    return stacks


def plain_reset(stack, source, baseline):
    return (source is not None and baseline is not None
            and set(stack) == set(baseline) == MODERN_PLAIN and set(source) == LEGACY_PLAIN
            and stack["id"] == source["id"] == baseline["id"]
            and stack["count"] == 1 and int(baseline["count"]) == int(source["Count"]) > 1)


def convert_saved_stack(stack, source, baseline, registered):
    item = str(stack["id"])
    if set(stack) != LEGACY_PLAIN:
        return None
    if (source is not None and baseline is not None
            and set(source) == LEGACY_PLAIN and set(baseline) == MODERN_PLAIN and source["id"] == item):
        item = str(baseline["id"])
    if item not in registered:
        return None
    return nbtlib.Compound({"id": nbtlib.String(item), "count": nbtlib.Int(stack["Count"]), "Slot": stack["Slot"]})


def verified_rename(source, baseline, registered):
    return (source is not None and baseline is not None
            and set(source) == LEGACY_PLAIN and set(baseline) == MODERN_PLAIN
            and source["id"] not in registered and baseline["id"] in registered
            and source["Count"] == baseline["count"])


def record_change(key, stack, updated, reason, counts, records):
    quantity = stack_count(stack) if stack is not None else 0
    row = {"dimension": key[0], "position": key[1:4], "slot": key[4],
           "before_item": str(stack["id"]) if stack is not None else None,
           "before_count": quantity, "kind": reason}
    if updated is not None:
        row.update(after_item=str(updated["id"]), after_count=stack_count(updated))
        counts["restored_item_quantity"] += stack_count(updated) - quantity
    counts[reason] += 1
    records.append(row)


def update_chunk(dimension, chunk, vaults, old, converted, registered, counts, records):
    slots = [((dimension, *position(entity), int(stack["Slot"])), items, index, stack)
             for entity in vaults for items in (vault_items(entity),) for index, stack in enumerate(items)]
    reset_candidates = {key for key, _, _, stack in slots
                        if plain_reset(stack, old.get(key), converted.get(key)) and stack["id"] in registered}
    # Require repeated 64-to-one resets in the same upgraded chunk before restoring counts.
    repeated_reset = chunk["DataVersion"] == 3955 and sum(old[k]["Count"] == 64 for k in reset_candidates) >= 2
    changed = False
    for key, items, index, stack in slots:
        updated = None
        reason = ""
        if "Count" in stack and "count" not in stack:
            updated = convert_saved_stack(stack, old.get(key), converted.get(key), registered)
            reason = "upgraded_stack_format" if updated is not None else "unresolved_legacy_stack"
        elif (set(stack) == MODERN_PLAIN and verified_rename(old.get(key), converted.get(key), registered)
              and stack["id"] == old[key]["id"]):
            updated = deepcopy(stack)
            updated["id"] = converted[key]["id"]
            reason = "renamed_unavailable_stack"
        elif key in reset_candidates and repeated_reset:
            updated = deepcopy(stack)
            updated["count"] = nbtlib.Int(converted[key]["count"])
            reason = "restored_reset_quantity"
        if reason:
            record_change(key, stack, updated, reason, counts, records)
            if updated is not None:
                items[index] = updated
                changed = True
    for entity in vaults:
        inventory = entity.get("Inventory")
        if not inventory:
            continue
        xyz = position(entity)
        items = vault_items(entity)
        occupied = {int(stack["Slot"]) for stack in items}
        for slot in range(int(inventory.get("Size", 0))):
            key = dimension, *xyz, slot
            original, baseline = old.get(key), converted.get(key)
            if slot in occupied or not verified_rename(original, baseline, registered):
                continue
            if not isinstance(items, nbtlib.List[nbtlib.Compound]):
                items = inventory["Items"] = nbtlib.List[nbtlib.Compound]()
            items.append(deepcopy(baseline))
            record_change(key, None, baseline, "recovered_renamed_stack", counts, records)
            changed = True
    return changed


def reconcile(world, source, reference, catalog, output):
    old, converted = read_stacks(source), read_stacks(reference)
    registered = set(catalog["items"])
    if "minecraft:air" not in registered:
        raise ValueError("Expected the target server's exported item registry")
    counts, records = Counter(), []
    with TemporaryDirectory(dir=output.parent) as directory:
        staging = Path(directory) / "world"
        shutil.copytree(world, staging, ignore=shutil.ignore_patterns("session.lock"))
        updated = None
        current = None
        for dimension, path, data, slot, offset, coords, chunk, vaults in vault_chunks(world):
            if path != current:
                if updated is not None:
                    (staging / current.relative_to(world)).write_bytes(updated)
                updated, current = None, path
            if not update_chunk(dimension, chunk, vaults, old, converted, registered, counts, records):
                continue
            if data[offset + 4] & 128:
                raise ValueError(f"Cannot rewrite an external vault chunk at {coords}")
            if updated is None:
                updated = bytearray(data)
            replace_chunk(updated, slot, offset, updated[slot + 3], chunk)
            counts["changed_chunks"] += 1
        if updated is not None:
            (staging / current.relative_to(world)).write_bytes(updated)
        staging.rename(output)
    return {"counts": counts, "slots": records}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("legacy_world", type=Path)
    parser.add_argument("converted_legacy_world", type=Path)
    parser.add_argument("target_registry", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    world, source, reference, output = (path.resolve() for path in
                                        (args.world, args.legacy_world, args.converted_legacy_world, args.output))
    if output.exists() or any(not path.is_dir() or output.is_relative_to(path)
                              for path in (world, source, reference)):
        parser.error("Pass three closed input worlds and a new output directory outside them")
    result = reconcile(world, source, reference, json.loads(args.target_registry.read_text()), output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
