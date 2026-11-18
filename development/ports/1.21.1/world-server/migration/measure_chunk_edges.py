#!/usr/bin/env python3
"""Measure retained terrain and seam height changes for prepared Overworld chunk pairs."""

import argparse
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import statistics
import zlib

import nbtlib


SECTOR = 4096


def read_chunk(regions, x, z, full=True):
    path = regions / f"r.{x // 32}.{z // 32}.mca"
    entry = ((x % 32) + 32 * (z % 32)) * 4
    if not path.exists():
        return None
    with path.open("rb") as file:
        file.seek(entry)
        offset = int.from_bytes(file.read(3), "big") * SECTOR
        if offset == 0:
            return None
        file.seek(offset)
        length = int.from_bytes(file.read(4), "big")
        kind = file.read(1)[0]
        if kind & 128:
            payload = (regions / f"c.{x}.{z}.mcc").read_bytes()
        else:
            payload = file.read(length - 1)
    kind &= 127
    if kind == 1:
        payload = gzip.decompress(payload)
    elif kind == 2:
        payload = zlib.decompress(payload)
    elif kind != 3:
        raise ValueError(f"Unsupported chunk compression {kind} for {x}, {z}")
    chunk = nbtlib.File.parse(io.BytesIO(payload))
    return chunk if not full or chunk["Status"] in {"minecraft:full", "full"} else None


def heights(chunk, minimum, height):
    packed = chunk["Heightmaps"]["MOTION_BLOCKING_NO_LEAVES"]
    bits = height.bit_length()
    per_long = 64 // bits
    mask = (1 << bits) - 1
    if len(packed) != (256 + per_long - 1) // per_long:
        raise ValueError("Unexpected heightmap width. Check the selected dimension's height.")
    return [
        minimum + ((int(packed[index // per_long]) >> (index % per_long * bits)) & mask)
        for index in range(256)
    ]


def border(values, dx, dz):
    if dx:
        column = 15 if dx > 0 else 0
        return [values[16 * z + column] for z in range(16)]
    row = 15 if dz > 0 else 0
    return values[row * 16 : row * 16 + 16]


def biomes(chunk, surface):
    sections = {int(section["Y"]): section["biomes"] for section in chunk.get("sections", ())
                if "biomes" in section}
    result = []
    for index, height in enumerate(surface):
        y = height - 1
        section = sections.get(y // 16)
        if section is None:
            result.append(None)
            continue
        palette = section["palette"]
        if len(palette) == 1:
            result.append(str(palette[0]))
            continue
        local = ((y & 15) >> 2) * 16 + (index // 64) * 4 + ((index & 15) >> 2)
        bits = (len(palette) - 1).bit_length()
        per_long = 64 // bits
        value = (int(section["data"][local // per_long]) >> (local % per_long * bits)) & ((1 << bits) - 1)
        result.append(str(palette[value]))
    return result


def transitions(first, second):
    transitions = Counter((a, b) for a, b in zip(first, second, strict=True) if a is not None and b is not None)
    return [{"from": a, "to": b, "columns": count} for (a, b), count in sorted(transitions.items())]


def difference(first, second):
    deltas = [right - left for left, right in zip(first, second, strict=True)]
    absolute = list(map(abs, deltas))
    return {
        "changed_columns": sum(delta != 0 for delta in deltas),
        "median_absolute_delta": statistics.median(absolute),
        "max_absolute_delta": max(absolute),
        "signed_deltas": deltas,
    }


def slope_profile(grid, dx, dz, seam_near):
    if dx:
        layers = [grid[x::16] for x in range(16)]
    else:
        layers = [grid[16 * z : 16 * z + 16] for z in range(16)]
    if dx < 0 or dz < 0:
        layers.reverse()
    if seam_near:
        layers = layers[-3:] if seam_near == "end" else layers[:3]
    values = sorted(abs(a - b) for before, after in zip(layers, layers[1:])
                    for a, b in zip(before, after, strict=True))
    return {"pairs": len(values), "median": statistics.median(values),
            "p95": values[(len(values) * 95 - 1) // 100], "max": max(values)}


def measure(old, migrated, edge, minimum, height):
    x0, z0, x1, z1 = edge
    dx = x1 - x0
    dz = z1 - z0
    if abs(dx) + abs(dz) != 1:
        raise ValueError(f"Chunk edges must share one side: {edge}")
    start = read_chunk(old, x0, z0)
    previous_neighbor = read_chunk(old, x1, z1, full=False)
    if start is None or (previous_neighbor is not None and previous_neighbor["Status"] in {"minecraft:full", "full"}):
        raise ValueError(f"Expected one original full chunk and an ungenerated adjacent chunk: {edge}")
    prior = read_chunk(migrated, x0, z0)
    generated = read_chunk(migrated, x1, z1)
    if prior is None or generated is None:
        raise ValueError(f"Both chunks must be fully saved in the migrated world: {edge}")
    old_height, migrated_height, new_height = [heights(chunk, minimum, height) for chunk in (start, prior, generated)]
    retained = difference(old_height, migrated_height)
    retained.pop("signed_deltas")
    seam = difference(border(migrated_height, dx, dz), border(new_height, -dx, -dz))
    return {
        "old_chunk": [x0, z0],
        "new_chunk": [x1, z1],
        "original_neighbor_status": str(previous_neighbor["Status"]) if previous_neighbor is not None else None,
        "retained_terrain": retained,
        "seam": seam,
        "surface_biomes": transitions(border(biomes(prior, migrated_height), dx, dz),
                                       border(biomes(generated, new_height), -dx, -dz)),
        "old_adjacent_gradients": slope_profile(migrated_height, dx, dz, None),
        "new_adjacent_gradients": slope_profile(new_height, dx, dz, None),
        "old_boundary_adjacent_gradients": slope_profile(migrated_height, dx, dz, "end"),
        "new_boundary_adjacent_gradients": slope_profile(new_height, dx, dz, "start"),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-regions", required=True, type=Path)
    parser.add_argument("--migrated-regions", required=True, type=Path)
    parser.add_argument("--edge", nargs=4, action="append", type=int, required=True,
                        metavar=("OLD_X", "OLD_Z", "NEW_X", "NEW_Z"))
    parser.add_argument("--min-y", type=int, default=-64)
    parser.add_argument("--height", type=int, default=384)
    options = parser.parse_args()
    report = [measure(options.old_regions, options.migrated_regions, edge, options.min_y, options.height)
              for edge in options.edge]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
