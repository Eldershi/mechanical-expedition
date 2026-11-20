#!/usr/bin/env python3
"""Merge converted legacy Create filter settings into a closed current world copy."""

import argparse
from pathlib import Path
import json

import nbtlib

from measure_chunk_edges import read_chunk
from prepare_region_copy import SECTOR, replace_chunk


COMPONENTS = {
    "create:filter": {"create:filter_items", "create:filter_items_blacklist",
                      "create:filter_items_respect_nbt"},
    "create:attribute_filter": {"create:attribute_filter_whitelist_mode",
                                "create:attribute_filter_matched_attributes"},
}


def component_keys(stack):
    return COMPONENTS.get(str(stack.get("id", "")), set()) & stack.get("components", {}).keys()


def restore_stack(old, current):
    if old.get("id") != current.get("id"):
        return current
    keys = component_keys(old)
    if not keys or component_keys(current) or current.get("tag"):
        return current
    current = current.copy()
    components = nbtlib.Compound(current.get("components", {}))
    for key in keys:
        components[key] = old["components"][key]
    if "minecraft:custom_name" in old["components"]:
        components.setdefault("minecraft:custom_name", old["components"]["minecraft:custom_name"])
    current["components"] = components
    return nbtlib.Compound(current)


def restore_entity(old, current):
    kind = current["id"]
    pairs = []
    if kind == "create:funnel" and "Filter" in old and "Filter" in current:
        pairs.append((old, "Filter", current, "Filter"))
    elif kind == "create:stock_ticker":
        before, after = old.get("Categories", ()), current.get("Categories", ())
        if len(before) == len(after) and all(a.get("id") == b.get("id") for a, b in zip(before, after)):
            pairs.extend((before, index, after, index) for index in range(len(before)))
    elif kind == "create:item_vault":
        before = {stack["Slot"]: stack for stack in old.get("Inventory", {}).get("Items", ())}
        after = current.get("Inventory", {}).get("Items", ())
        pairs.extend((before, stack["Slot"], after, index) for index, stack in enumerate(after)
                     if stack["Slot"] in before)
    count = 0
    for before, source_key, after, target_key in pairs:
        upgraded = restore_stack(before[source_key], after[target_key])
        if upgraded != after[target_key]:
            after[target_key] = upgraded
            count += 1
    return count


def position(entity):
    return tuple(entity[key] for key in "xyz")


def configured_stacks(entity):
    if entity["id"] == "create:funnel":
        return (entity.get("Filter", {}),)
    if entity["id"] == "create:stock_ticker":
        return entity.get("Categories", ())
    if entity["id"] == "create:item_vault":
        return entity.get("Inventory", {}).get("Items", ())
    return ()


def repair(converted, current, output):
    report = {}
    for source_file in sorted(converted.glob("r.*.mca")):
        target_file = current / source_file.name
        if not target_file.is_file():
            continue
        source_header = source_file.open("rb").read(SECTOR)
        rx, rz = map(int, source_file.name.split(".")[1:3])
        region = None
        count = 0
        for offset in range(0, SECTOR, 4):
            if not int.from_bytes(source_header[offset:offset + 3], "big"):
                continue
            slot = offset // 4
            cx, cz = rx * 32 + slot % 32, rz * 32 + slot // 32
            old = read_chunk(converted, cx, cz, full=False)
            originals = {(position(entity), entity["id"]): entity for entity in old.get("block_entities", ())
                         if any(component_keys(stack) for stack in configured_stacks(entity))}
            if not originals:
                continue
            new = read_chunk(current, cx, cz)
            if new is None:
                continue
            restored = sum(restore_entity(originals.get((position(entity), entity["id"]), {}), entity)
                           for entity in new.get("block_entities", ()))
            if not restored:
                continue
            if region is None:
                region = bytearray(target_file.read_bytes())
            start = int.from_bytes(region[offset:offset + 3], "big") * SECTOR
            if region[start + 4] & 128:
                raise ValueError(f"External region chunk at {(cx, cz)}")
            replace_chunk(region, offset, start, region[offset + 3], new)
            count += restored
        if region is not None:
            (output / source_file.name).write_bytes(region)
            report[source_file.name] = count
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("converted_regions", type=Path)
    parser.add_argument("current_regions", type=Path)
    parser.add_argument("overlay", type=Path)
    args = parser.parse_args()
    output = args.overlay.resolve()
    if output.exists() or any(path.resolve() in output.parents
                              for path in (args.converted_regions, args.current_regions)):
        parser.error("Choose a new output directory outside the input regions")
    output.mkdir(parents=True)
    print(json.dumps(repair(args.converted_regions, args.current_regions, output)))


if __name__ == "__main__":
    main()
