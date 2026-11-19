#!/usr/bin/env python3
"""Apply verified, stateless block ID replacements to a new closed world copy."""

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import nbtlib
import numpy as np

from audit_block_palettes import AIR, properties, region_chunks, terrain_regions
from migrate_quartz_and_peat import read_indices, write_indices
from prepare_region_copy import replace_chunk

MAPPINGS = Path(__file__).with_name("retired_block_mappings.json")


def block_position(chunk, section, index):
    return (int(chunk["xPos"]) * 16 + index % 16,
            int(section["Y"]) * 16 + index // 256,
            int(chunk["zPos"]) * 16 + index // 16 % 16)


def update_chunk(chunk, dimension, targets, catalog, counts, examples):
    entities = {tuple(int(entity[k]) for k in "xyz") for entity in chunk.get("block_entities", ())}
    changed = False
    for section in chunk.get("sections", ()):
        states = section.get("block_states", {})
        palette = list(states.get("palette", ()))
        selected = [(index, str(entry["Name"])) for index, entry in enumerate(palette)
                    if entry["Name"] in targets]
        if not selected:
            continue
        values = read_indices(states, len(palette))
        section_changed = False
        for index, old in selected:
            occupied = np.flatnonzero(values == index)
            if not occupied.size:
                continue
            state = properties(palette[index])
            new, required_state = targets[old]
            if required_state is not None and state != required_state:
                continue
            schema = catalog[new]["properties"]
            position = block_position(chunk, section, int(occupied[0]))
            if state.keys() != schema.keys() or any(value not in schema[key] for key, value in state.items()):
                raise ValueError(f"State {old} {state} at {position} does not match {new}")
            for entity in entities:
                x, y, z = entity
                if y // 16 == int(section["Y"]) and values[(y % 16) * 256 + (z % 16) * 16 + x % 16] == index:
                    raise ValueError(f"{old} at {entity} has a saved block entity")
            palette[index]["Name"] = nbtlib.String(new)
            counts[old] += int(occupied.size)
            seen = examples.setdefault(old, [])
            if len(seen) < 8 and not any(
                row["dimension"] == dimension and row["position"][0] // 16 == position[0] // 16
                and row["position"][2] // 16 == position[2] // 16 for row in seen
            ):
                seen.append({"dimension": dimension, "position": position, "target": new, "properties": state})
            section_changed = True
        if section_changed:
            compact = []
            remap = []
            keys = {}
            for entry in palette:
                key = str(entry["Name"]), tuple(properties(entry).items())
                if key not in keys:
                    keys[key] = len(compact)
                    compact.append(entry)
                remap.append(keys[key])
            write_indices(states, compact, np.asarray(remap, dtype=np.uint64)[values])
            changed = True
    return changed


def remap(world, output, targets, catalog):
    rules = {}
    for old, rule in targets.items():
        new, required_state = (rule, None) if isinstance(rule, str) else (rule["target"], rule["properties"])
        block = catalog.get(new)
        if old in catalog or block is None or new in AIR or block["air"]:
            raise ValueError(f"Invalid stateless replacement {old} -> {new}")
        if block["block_entity"] and required_state not in block.get("states_without_entity", ()):
            raise ValueError(f"Target {new} can create a block entity in the selected states")
        rules[old] = new, required_state
    markers = tuple(name.encode() for name in targets)
    counts, examples = Counter(), {}
    changed_chunks, changed_regions = 0, 0
    with TemporaryDirectory(dir=output.parent) as temp:
        staging = Path(temp) / "world"
        shutil.copytree(world, staging, ignore=shutil.ignore_patterns("session.lock"))
        for dimension, path in terrain_regions(world):
            original = path.read_bytes()
            updated = None
            for slot, offset, coords, payload in region_chunks(path, original):
                if not any(marker in payload for marker in markers):
                    continue
                chunk = nbtlib.File.parse(io.BytesIO(payload))
                if coords != (int(chunk["xPos"]), int(chunk["zPos"])):
                    raise ValueError(f"Misplaced source chunk at {coords} in {path.name}")
                if update_chunk(chunk, dimension, rules, catalog, counts, examples):
                    if original[offset + 4] & 128:
                        raise ValueError(f"Cannot rewrite an external chunk at {coords}")
                    if updated is None:
                        updated = bytearray(original)
                    replace_chunk(updated, slot, offset, original[slot + 3], chunk)
                    changed_chunks += 1
            if updated is not None:
                (staging / path.relative_to(world)).write_bytes(updated)
                changed_regions += 1
        staging.rename(output)
    return {"chunks": changed_chunks, "regions": changed_regions,
            "total": sum(counts.values()), "blocks": {
                old: {"target": rules[old][0], "count": count, "examples": examples[old]}
                for old, count in counts.most_common()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    world, output = args.world.resolve(), args.output.resolve()
    if not world.is_dir() or output.exists() or output.is_relative_to(world):
        parser.error("Pass a closed source world and a new output directory outside it")
    result = remap(world, output, json.loads(MAPPINGS.read_text()), json.loads(args.catalog.read_text())["blocks"])
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
