#!/usr/bin/env python3
"""Restore Rock & Stone deposit records from a closed, older Anvil archive."""

import argparse
from collections import Counter
from copy import deepcopy
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import nbtlib
import numpy as np

from measure_chunk_edges import read_chunk
from migrate_quartz_and_peat import BLOCKS, read_indices, write_indices
from prepare_region_copy import SECTOR, read_payload, replace_chunk


NODE_NAMES = {"aluminum", "platinum", "vanadium", "oil_shale", "coal", "iron", "cheese"}
LEGACY_STARTS = {f"cmi:ore_node/{kind}_node" for kind in NODE_NAMES}
LEGACY_BLOCKS = {f"cmi:{kind}_deposit_block" for kind in NODE_NAMES} | {
    name for name, output in BLOCKS.items() if output.endswith("_deposit_block")
}
BEARING = "create_rns:miner_bearing"
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}
MARKERS = tuple(name.encode() for name in LEGACY_STARTS | LEGACY_BLOCKS | {BEARING})


def recovery_candidates(chunk):
    selected = []
    for section in chunk.get("sections", ()):
        for index, state in enumerate(section.get("block_states", {}).get("palette", ())):
            if state["Name"] in LEGACY_BLOCKS:
                selected.append((section, index, state))
    return selected


def restore_blocks(targets, affected, counts):
    for section, old_index, saved in affected:
        y = int(section["Y"])
        if y not in targets:
            raise ValueError(f"Missing prepared block section {y}")
        origin = section["block_states"]
        existing = targets[y]["block_states"]
        wanted = deepcopy(saved)
        name = str(wanted["Name"])
        wanted["Name"] = nbtlib.String(BLOCKS.get(name, name))
        source_indices = read_indices(origin, len(origin["palette"]))
        saved_positions = np.flatnonzero(source_indices == old_index)
        palette = list(existing["palette"])
        indices = read_indices(existing, len(palette))
        if wanted not in palette:
            palette.append(wanted)
        wanted_index = palette.index(wanted)
        replaced = 0
        for position in saved_positions:
            state = palette[indices[position]]
            if state == wanted:
                counts[f"already_present/{name}"] += 1
            elif state["Name"] in AIR or state == saved:
                indices[position] = wanted_index
                replaced += 1
            else:
                raise ValueError(f"Occupied legacy deposit block at section {y}, index {position}")
        if replaced:
            counts[f"restored_blocks/{name}"] += replaced
            write_indices(existing, palette, indices)


def restore_structure_data(source, target, counts):
    for kind in ("starts", "References"):
        for key, state in source.get("structures", {}).get(kind, {}).items():
            if key not in LEGACY_STARTS:
                continue
            structures = target.setdefault("structures", nbtlib.Compound())
            section = structures.setdefault(kind, nbtlib.Compound())
            if key not in section:
                section[key] = state
                counts[f"restored_{kind}/{key}"] += 1


def restore_bearings(source, target, counts):
    originals = {tuple(e[k] for k in "xyz"): e["process"] for e in source.get("block_entities", ())
                 if e.get("id") == BEARING and "process" in e}
    for entry in target.get("block_entities", ()):
        if entry.get("id") != BEARING:
            continue
        position = tuple(entry[k] for k in "xyz")
        process = originals.pop(position, None)
        if process is not None and "process" not in entry:
            entry["process"] = process
            for stage in process.get("inner_processes", ()):
                name = stage.get("deposit_block")
                if name in BLOCKS:
                    stage["deposit_block"] = nbtlib.String(BLOCKS[name])
            counts["restored_bearing_processes"] += 1
    if originals:
        raise ValueError("Legacy mining process has no matching bearing in the prepared chunk")


def restore_region(old_path, target_path, out_path):
    original = old_path.read_bytes()
    rx, rz = map(int, old_path.name.split(".")[1:3])
    updated = None
    report = Counter()
    for slot in range(1024):
        index = slot * 4
        old_offset = int.from_bytes(original[index:index + 3], "big") * SECTOR
        if not old_offset:
            continue
        coords = (rx * 32 + slot % 32, rz * 32 + slot // 32)
        payload = read_payload(original, old_offset, coords, old_path)
        if not any(marker in payload for marker in MARKERS):
            continue
        old = nbtlib.File.parse(io.BytesIO(payload))
        candidates = recovery_candidates(old)
        has_starts = any(
            LEGACY_STARTS.intersection(old.get("structures", {}).get(kind, {}))
            for kind in ("starts", "References")
        )
        has_bearing_process = any(e.get("id") == BEARING and "process" in e for e in old.get("block_entities", ()))
        if not (candidates or has_starts or has_bearing_process):
            continue
        current = read_chunk(target_path.parent, *coords, full=False)
        if current is None:
            if candidates or has_bearing_process:
                raise ValueError(f"Missing prepared chunk with an archived deposit or bearing at {coords}")
            report["structure_reference_chunks_outside_prepared_world"] += 1
            continue
        per_chunk = Counter()
        sections = {int(section["Y"]): section for section in current.get("sections", ())}
        restore_blocks(sections, candidates, per_chunk)
        restore_structure_data(old, current, per_chunk)
        restore_bearings(old, current, per_chunk)
        report.update(per_chunk)
        if not any(key.startswith("restored_") and value for key, value in per_chunk.items()):
            continue
        if updated is None:
            updated = bytearray(target_path.read_bytes())
        offset = int.from_bytes(updated[index:index + 3], "big") * SECTOR
        if updated[offset + 4] & 128:
            raise ValueError(f"External prepared chunk at {coords}")
        replace_chunk(updated, index, offset, updated[index + 3], current)
    if updated is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(updated)
    return report


def restore(source, prepared, output):
    if output.exists() or output.is_relative_to(source) or output.is_relative_to(prepared):
        raise ValueError("Pass a new output directory outside both closed world copies")
    report = Counter()
    with TemporaryDirectory(dir=output.parent) as directory:
        staging = Path(directory) / "changes"
        staging.mkdir()
        for path in sorted(source.rglob("r.*.mca")):
            if path.parent.name != "region":
                continue
            relative = path.relative_to(source)
            report.update(restore_region(path, prepared / relative, staging / relative))
        staging.rename(output)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("prepared", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(restore(args.archive.resolve(), args.prepared.resolve(), args.output.resolve()),
                     sort_keys=True, indent=2))
