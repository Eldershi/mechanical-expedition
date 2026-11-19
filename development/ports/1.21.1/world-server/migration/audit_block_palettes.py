#!/usr/bin/env python3
"""Audit occupied Anvil block states against the target server's block catalog."""

import argparse
from collections import Counter
import csv
import gzip
from itertools import groupby
import io
import json
from pathlib import Path
import re

import nbtlib
import numpy as np

from migrate_quartz_and_peat import read_indices
from prepare_region_copy import SECTOR, read_payload

REGION = re.compile(r"r\.(-?\d+)\.(-?\d+)\.mca")
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air"}


def terrain_regions(world):
    for path in sorted(world.rglob("r.*.mca")):
        if path.parent.name != "region" or not REGION.fullmatch(path.name):
            continue
        dimension = path.parent.parent.relative_to(world).parts
        if not dimension:
            yield "minecraft:overworld", path
        elif dimension == ("DIM-1",):
            yield "minecraft:the_nether", path
        elif dimension == ("DIM1",):
            yield "minecraft:the_end", path
        elif len(dimension) >= 3 and dimension[0] == "dimensions":
            yield f"{dimension[1]}:{'/'.join(dimension[2:])}", path
        else:
            yield "/".join(dimension), path


def region_chunks(path, data):
    if not data:
        return
    if len(data) < 2 * SECTOR:
        raise ValueError(f"Incomplete Anvil header in {path.name}")
    rx, rz = map(int, REGION.fullmatch(path.name).groups())
    for slot in range(1024):
        index = slot * 4
        offset = int.from_bytes(data[index:index + 3], "big") * SECTOR
        if not offset:
            continue
        coords = (rx * 32 + slot % 32, rz * 32 + slot // 32)
        allocation = data[index + 3] * SECTOR
        if not 2 * SECTOR <= offset <= len(data) - 5 or allocation == 0:
            raise ValueError(f"Invalid Anvil chunk offset in {path.name} at {coords}")
        length = int.from_bytes(data[offset:offset + 4], "big")
        if not 1 <= length <= min(allocation, len(data) - offset) - 4:
            raise ValueError(f"Invalid Anvil payload length in {path.name} at {coords}")
        yield index, offset, coords, read_payload(data, offset, coords, path)


def properties(state):
    return {key: str(value) for key, value in sorted(state.get("Properties", {}).items())}


def category(name, entity, area):
    key = name.split(":", 1)[-1]
    if area == "generated_structure":
        return area
    if entity:
        return "player_machine" if area == "industrial" else "block_entity"
    if re.search(r"(?:^|_)(?:ore|deposit_block)(?:_|$)", key):
        return "ore_or_deposit"
    if re.search(r"(?:^|_)(?:stairs|slab|wall|bricks?|fence|door|trapdoor|tiles?|pillar|beam|roof|window|planks|siding|casing|chiseled|pane)(?:_|$)", key):
        return "player_construction" if area == "industrial" else "construction"
    if re.search(r"(?:^|_)(?:tank|machine|factory|cable|pipe|pump|motor|crusher|press|burner|heater|conveyor|generator|battery|terminal|engine|gearbox|valve|connector)(?:_|$)", key):
        return "possible_machine"
    return "other_material_or_terrain"


def run_positions(indices):
    for _, row in groupby(map(int, indices), key=lambda pos: pos // 16):
        for _, segment in groupby(enumerate(row), key=lambda pair: pair[1] - pair[0]):
            run = [pos for _, pos in segment]
            position = run[0]
            yield position % 16, run[-1] % 16, position // 256, position // 16 % 16


def inside(point, area):
    return all(lo <= coordinate <= hi for coordinate, lo, hi in zip(point, area["min"], area["max"], strict=True))


def audit(world, catalog, output, areas=(), discovery=False):
    blocks, fixes = catalog["blocks"], catalog.get("fixes", {})
    totals = Counter()
    locations = {}
    coverage = {}
    native = Counter()
    unprobed = set()
    with gzip.open(output / "positions.tsv.gz", "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(("dimension", "y", "z", "x_start", "x_end", "old_block", "properties_json", "category", "block_entity"))
        for dimension, path in terrain_regions(world):
            summary = coverage.setdefault(dimension, Counter())
            summary["regions"] += 1
            for _, _, (cx, cz), payload in region_chunks(path, path.read_bytes()):
                chunk = nbtlib.File.parse(io.BytesIO(payload))
                summary["chunks"] += 1
                version = int(chunk["DataVersion"])
                summary[f"data_version/{version}"] += 1
                summary[f"status/{chunk['Status']}"] += 1
                if "Level" in chunk:
                    raise ValueError(f"Legacy nested section format in {path.name}, chunk {(cx, cz)}")
                if int(chunk["xPos"]) != cx or int(chunk["zPos"]) != cz:
                    raise ValueError(f"Misplaced chunk in {path.name} at {(cx, cz)}")
                entities = {tuple(int(entry[key]) for key in "xyz"): str(entry.get("id", "unknown"))
                            for entry in chunk.get("block_entities", ())}
                nearby = [area for area in areas if area["dimension"] == dimension
                          and area["min"][0] // 16 <= cx <= area["max"][0] // 16
                          and area["min"][2] // 16 <= cz <= area["max"][2] // 16]
                for section in chunk.get("sections", ()):
                    states = section.get("block_states", {})
                    palette = states.get("palette", ())
                    missing = []
                    for index, entry in enumerate(palette):
                        old = str(entry["Name"])
                        if old in blocks or old in AIR:
                            continue
                        state = json.dumps(properties(entry), sort_keys=True, separators=(",", ":"))
                        missing.append((index, old, state))
                    if not missing:
                        continue
                    values = read_indices(states, len(palette))
                    sy = int(section["Y"]) * 16
                    for index, name, state in missing:
                        occupied = np.flatnonzero(values == index)
                        if not occupied.size:
                            continue
                        key = f"{version}/{name}/{state}"
                        fix = fixes.get(key)
                        if fix is None:
                            unprobed.add((version, name, state))
                        elif fix["resolved"] in blocks and fix["resolved"] not in AIR:
                            native[(name, fix["resolved"])] += occupied.size
                            continue
                        totals[name] += occupied.size
                        info = locations.setdefault(name, {"category_counts": Counter(), "dimension_counts": Counter(),
                                                           "states": Counter(), "block_entities": Counter(), "examples": [],
                                                           "regions": Counter(), "data_versions": Counter()})
                        info["dimension_counts"][dimension] += occupied.size
                        info["data_versions"][version] += occupied.size
                        info["states"][state] += occupied.size
                        info["regions"][f"{dimension}/{path.name}"] += occupied.size
                        matching = [area for area in nearby if any(name.startswith(p) for p in area["prefixes"])]
                        for start, end, dy, dz in run_positions(occupied):
                            y, z = sy + dy, cz * 16 + dz
                            start, end = cx * 16 + start, cx * 16 + end
                            entries = ((x, entities.get((x, y, z), ""),
                                        next((area["kind"] for area in matching if inside((x, y, z), area)), ""))
                                       for x in range(start, end + 1))
                            for (entity, area), subrun in groupby(entries, key=lambda entry: entry[1:]):
                                xs = [x for x, _, _ in subrun]
                                kind = category(name, entity, area)
                                writer.writerow((dimension, y, z, xs[0], xs[-1], name, state, kind, entity))
                                info["category_counts"][kind] += len(xs)
                                if entity:
                                    info["block_entities"][entity] += len(xs)
                                if len(info["examples"]) < 5:
                                    info["examples"].append([dimension, xs[0], y, z])
    if unprobed:
        with (output / "legacy-block-states.jsonl").open("w") as handle:
            for row in sorted(unprobed):
                print(json.dumps(row), file=handle)
        if not discovery:
            raise ValueError("Native decode results are missing for occupied states. Probe legacy-block-states.jsonl before using this report.")
    return {"coverage": coverage, "total": sum(totals.values()),
            "unprobed_states": len(unprobed),
            "native_conversions": [{"old": old, "target": target, "count": count}
                                   for (old, target), count in sorted(native.items())],
            "blocks": {name: {"count": count, **locations[name]} for name, count in totals.most_common()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--areas", type=Path)
    parser.add_argument("--discovery", action="store_true", help="List occupied states that still need native decoding")
    args = parser.parse_args()
    world, output = args.world.resolve(), args.output.resolve()
    if not world.is_dir() or output.is_relative_to(world):
        parser.error("Pass an existing world and a new report directory outside it")
    output.mkdir()
    areas = json.loads(args.areas.read_text()) if args.areas else ()
    summary = audit(world, json.loads(args.catalog.read_text()), output, areas, args.discovery)
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"{summary['total']} occupied fallback blocks across {len(summary['blocks'])} IDs")


if __name__ == "__main__":
    main()
