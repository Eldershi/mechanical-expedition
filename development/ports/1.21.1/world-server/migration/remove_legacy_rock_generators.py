#!/usr/bin/env python3
"""Remove retired Thermal rock generators and their saved items from a closed world copy."""

import argparse
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import nbtlib
import numpy as np

from audit_block_palettes import REGION, region_chunks, terrain_regions
from migrate_quartz_and_peat import read_indices, write_indices
from prepare_region_copy import replace_chunk
from remap_retired_blocks import block_position

DEVICE = "thermal:device_rock_gen"
MARKER = DEVICE.encode()
AIR = nbtlib.Compound({"Name": nbtlib.String("minecraft:air")})
NUMERIC = (nbtlib.Byte, nbtlib.Short, nbtlib.Int, nbtlib.Long)


def remove_placed(chunk, dimension, locations):
    removed = set()
    for section in chunk.get("sections", ()):
        states = section.get("block_states", {})
        palette = list(states.get("palette", ()))
        indices = [i for i, entry in enumerate(palette) if entry["Name"] == DEVICE]
        if not indices:
            continue
        values = read_indices(states, len(palette))
        selected = set(indices)
        for index in np.flatnonzero(np.isin(values, indices)):
            removed.add(block_position(chunk, section, int(index)))
        kept = [state for i, state in enumerate(palette) if i not in selected]
        if AIR not in kept:
            kept.append(AIR)
        air_index = kept.index(AIR)
        remap = np.asarray([air_index if i in selected else kept.index(state)
                            for i, state in enumerate(palette)], dtype=np.intp)
        write_indices(states, kept, remap[values])
    entities = chunk.get("block_entities", ())
    device_entities = [e for e in entities if e.get("id") == DEVICE]
    saved = [tuple(int(e[k]) for k in "xyz") for e in device_entities]
    if len(saved) != len(removed) or set(saved) != removed:
        raise ValueError(f"Rock generator blocks and block entities disagree at chunk {chunk['xPos']}, {chunk['zPos']}")
    if not removed:
        return
    chunk["block_entities"] = type(entities)(e for e in entities if e.get("id") != DEVICE)
    if "block_ticks" in chunk:
        ticks = chunk["block_ticks"]
        chunk["block_ticks"] = type(ticks)(tick for tick in ticks if tick.get("i") != DEVICE)
    chunk.pop("Heightmaps", None)
    chunk.pop("isLightOn", None)
    for section in chunk["sections"]:
        section.pop("SkyLight", None)
        section.pop("BlockLight", None)
    locations.extend({"dimension": dimension, "position": xyz} for xyz in sorted(removed))


def item_quantity(node):
    if isinstance(node, nbtlib.Compound) and node.get("id") == DEVICE:
        amount = node.get("realCount", node.get("count", node.get("Count")))
        if isinstance(amount, NUMERIC) and amount > 0:
            return int(amount)
    return 0


def clear_contents(node, counts, field=""):
    if isinstance(node, nbtlib.Compound):
        for key, child in list(node.items()):
            if amount := item_quantity(child):
                counts["saved_items_removed"] += amount
                del node[key]
            else:
                clear_contents(child, counts, key)
    elif isinstance(node, nbtlib.List):
        for index in reversed(range(len(node))):
            entry = node[index]
            if field in {"recipes", "toBeDisplayed", "known", "highlight"} and entry == DEVICE:
                del node[index]
                counts["recipe_entries_removed"] += 1
                continue
            dropped = isinstance(entry, nbtlib.Compound) and entry.get("id") == "minecraft:item"
            amount = item_quantity(entry.get("Item")) if dropped else item_quantity(entry)
            if amount:
                counts["saved_items_removed"] += amount
                if dropped:
                    counts["dropped_entities_removed"] += 1
                if field in {"HandItems", "ArmorItems"}:
                    node[index] = nbtlib.Compound()
                else:
                    del node[index]
            else:
                clear_contents(entry, counts, field)


def checked_payload(root):
    buffer = io.BytesIO()
    root.write(buffer)
    payload = buffer.getvalue()
    if MARKER in payload:
        raise ValueError("Unsupported rock generator reference remains in the saved data")
    return payload


def change_region(path, world, dimension, counts, locations):
    before = path.read_bytes()
    changed = None
    for slot, offset, coords, payload in region_chunks(path, before):
        if MARKER not in payload:
            continue
        chunk = nbtlib.File.parse(io.BytesIO(payload))
        try:
            if dimension is not None:
                if coords != (int(chunk["xPos"]), int(chunk["zPos"])):
                    raise ValueError("Misplaced terrain chunk")
                remove_placed(chunk, dimension, locations)
            clear_contents(chunk, counts)
            checked_payload(chunk)
            if before[offset + 4] & 128:
                raise ValueError("Cannot rewrite an external chunk")
            if changed is None:
                changed = bytearray(before)
            replace_chunk(changed, slot, offset, before[slot + 3], chunk)
        except ValueError as error:
            raise ValueError(f"{path.relative_to(world)} chunk {coords}: {error}") from error
        counts["chunks_written"] += 1
    if changed is not None:
        path.write_bytes(changed)
        counts["region_files_written"] += 1


def remove(world, output):
    counts, locations = Counter(), []
    with TemporaryDirectory(dir=output.parent) as temp:
        staging = Path(temp) / "world"
        shutil.copytree(world, staging, ignore=shutil.ignore_patterns("session.lock"))
        dimensions = {path: dimension for dimension, path in terrain_regions(staging)}
        for path in sorted(staging.rglob("*")):
            if not path.is_file():
                continue
            if REGION.fullmatch(path.name) and path.parent.name in {"region", "entities", "poi"}:
                change_region(path, staging, dimensions.get(path), counts, locations)
            elif path.suffix in {".dat", ".dat_old", ".nbt"}:
                payload = path.read_bytes()
                compressed = payload.startswith(b"\x1f\x8b")
                payload = gzip.decompress(payload) if compressed else payload
                if MARKER in payload:
                    root = nbtlib.File.parse(io.BytesIO(payload))
                    clear_contents(root, counts)
                    cleaned = checked_payload(root)
                    path.write_bytes(gzip.compress(cleaned) if compressed else cleaned)
                    counts["nbt_files_written"] += 1
            elif path.suffix == ".zip":
                with ZipFile(path) as archive:
                    if any(MARKER in archive.read(member) for member in archive.namelist()):
                        raise ValueError(f"Rock generator reference in {path.relative_to(staging)}")
            elif path.suffix != ".mcc" and path.parent.name != "stats" and MARKER in path.read_bytes():
                raise ValueError(f"Rock generator reference in {path.relative_to(staging)}")
        staging.rename(output)
    return {"counts": dict(counts, placed_blocks_removed=len(locations)), "positions": locations}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    world, output = args.world.resolve(), args.output.resolve()
    if not (world / "level.dat").is_file() or output.exists() or output.is_relative_to(world):
        parser.error("Pass a closed source world and a new output directory outside it")
    print(json.dumps(remove(world, output), indent=2))
