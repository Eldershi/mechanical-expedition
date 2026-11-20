#!/usr/bin/env python3
"""Rebuild a terrain transition from the unmodified surface and a reviewed footprint."""

import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path

import nbtlib
import numpy as np

from measure_chunk_edges import read_chunk
from repair_terrain_transitions import AIR_BLOCKS, MODDED_GROUND, NATURAL_TICKS, natural_surface
from splice_overworld_island import (
    AIR, CELLS, HEIGHT, HEIGHTMAPS, LEVELS, MIN_Y, Palette, Writer, arrays, block,
    heights, is_natural_ground, pack, smooth,
)


PAD = 16
WATER = "minecraft:water"
AQUATIC = {"minecraft:kelp", "minecraft:kelp_plant", "minecraft:seagrass", "minecraft:tall_seagrass"}
DEEP_BED = {"minecraft:gravel", "minecraft:mud", "minecraft:clay", "minecraft:sand"}
TIMED_NATURE = AQUATIC | AIR_BLOCKS | {WATER, "minecraft:dirt", "minecraft:grass_block"}


def ground(states, palette, heightmap):
    soil = [i for i, state in enumerate(palette.states)
            if is_natural_ground(state["Name"]) or state["Name"] in MODDED_GROUND - {
                "spawn:sea_urchin", "spawn:sea_star", "supplementaries:barnacles"
            }]
    solid = np.isin(states, soil) & (LEVELS <= heightmap)
    return np.where(solid.any(axis=0), MIN_Y + HEIGHT - 1 - np.argmax(solid[::-1], axis=0), heightmap)


def blur(values):
    """Separable Gaussian with a two-block radius."""
    weights = np.array([1, 4, 6, 4, 1]) / 16
    for axis in (0, 1):
        view = np.moveaxis(values, axis, 0)
        padded = np.pad(view, ((2, 2), (0, 0)), mode="edge")
        values = np.moveaxis(sum(w * padded[i:i + view.shape[0]]
                                 for i, w in enumerate(weights)), 0, axis)
    return values


def terrain_field(before, published, region, affected, sea, exclusions, seabed_review):
    rx, rz = region
    x0, z0 = rx * 512 - PAD, rz * 512 - PAD
    side = 512 + 2 * PAD
    native = np.full((side, side), sea - 4, dtype=float)
    proposed = native.copy()
    valid = np.zeros((side, side), dtype=bool)
    edited = valid.copy()
    rooted = valid.copy()
    mud = valid.copy()
    sand = valid.copy()
    for cz in range(z0 // 16, (z0 + side) // 16):
        for cx in range(x0 // 16, (x0 + side) // 16):
            a, b = read_chunk(before, cx, cz), read_chunk(published, cx, cz)
            if a is None or b is None or "Heightmaps" not in a or "Heightmaps" not in b:
                continue
            z, x = cz * 16 - z0, cx * 16 - x0
            slot = np.s_[z:z + 16, x:x + 16]
            palette = Palette(nbtlib.Compound, keyed=True)
            pristine = arrays(a, palette)
            previous = arrays(b, palette)
            old_floor = ground(pristine, palette, heights(a)["OCEAN_FLOOR"] - 1)
            new_floor = ground(previous, palette, heights(b)["OCEAN_FLOOR"] - 1)
            names = np.array([str(state["Name"]) for state in palette.states])
            top = names[pristine[old_floor - MIN_Y, CELLS]]
            trunk = np.char.endswith(names, "_log") | np.char.endswith(names, "_wood")
            above = (LEVELS > old_floor) & (LEVELS <= old_floor + 3)
            native[slot] = old_floor.reshape(16, 16)
            proposed[slot] = new_floor.reshape(16, 16)
            valid[slot] = True
            rooted[slot] = (np.count_nonzero(trunk[pristine] & above, axis=0) >= 2).reshape(16, 16)
            mud[slot] = (top == "minecraft:mud").reshape(16, 16)
            sand[slot] = (top == "minecraft:sand").reshape(16, 16)
            if (cx, cz) in affected:
                edited[slot] = np.any(pristine != previous, axis=0).reshape(16, 16)
    z, x = np.ogrid[z0:z0 + side, x0:x0 + side]
    for x1, z1, x2, z2 in exclusions:
        distance = np.hypot(np.maximum(0, np.maximum(x1 - x, x - x2)),
                            np.maximum(0, np.maximum(z1 - z, z - z2)))
        retain = smooth(distance / 24)
        proposed = native + (proposed - native) * retain
    # Give the coastline a continuous profile while pinning existing dry woodland
    # and tree roots to the terrain that supports them.
    dry = (native >= sea + 1) & (proposed >= sea + 1)
    pinned = (dry & (np.abs(proposed - native) <= 13)) | (rooted & (native >= sea + 1))
    reference = np.where(pinned | ~edited, native, proposed)
    for _ in range(4):
        smooth_height = blur(reference * valid) / np.maximum(0.01, blur(valid.astype(float)))
        reference = np.where(pinned | ~edited, native, smooth_height)
    # Review narrow isolated bed protrusions even when their original columns
    # happened to be skipped by the first transition.
    neighbors = np.lib.stride_tricks.sliding_window_view(np.pad(reference, 2, mode="edge"), (5, 5))
    surrounding = np.median(neighbors, axis=(2, 3))
    seabed = np.zeros_like(valid)
    for x1, z1, x2, z2 in seabed_review:
        interior = np.minimum(np.minimum(x - x1, x2 - x), np.minimum(z - z1, z2 - z))
        strength = smooth(interior / 12)
        needles = valid & (reference <= sea + 3) & (surrounding <= sea - 1) & (reference - surrounding >= 4)
        cut = np.where(needles, np.maximum(0, reference - surrounding - 1) * strength, 0)
        seabed |= cut >= 0.5
        reference -= cut
    return np.rint(reference).astype(int), blur(mud.astype(float)), blur(sand.astype(float)), seabed


def structure_boxes(regions):
    @lru_cache(maxsize=160)
    def starts(x, z):
        chunk = read_chunk(regions, x, z, full=False)
        return chunk.get("structures", {}).get("starts", {}) if chunk is not None else {}

    def signed(value):
        return (value + (1 << 31)) % (1 << 32) - (1 << 31)

    def from_chunk(chunk):
        metadata = chunk.get("structures", {})
        nearby = list(metadata.get("starts", {}).values())
        for name, references in metadata.get("References", {}).items():
            for reference in references:
                structure = starts(signed(int(reference)), signed(int(reference) >> 32)).get(name)
                if structure is None:
                    return None
                nearby.append(structure)
        return [tuple(map(int, piece["BB"])) for structure in nearby for piece in structure.get("Children", ())
                if len(piece.get("BB", ())) == 6]
    return from_chunk


def rework(before, published, current, target, mud, sand, seabed, sea, boxes, tally):
    palette = Palette(nbtlib.Compound, keyed=True)
    pristine, previous, active = [arrays(chunk, palette) for chunk in (before, published, current)]
    base_maps = heights(before)
    original_floor = ground(pristine, palette, base_maps["OCEAN_FLOOR"] - 1)
    planned = np.any(pristine != previous, axis=0) | seabed
    names = np.array([str(state["Name"]) for state in palette.states])
    effective = pristine.copy()
    air = palette.index(block(AIR))
    water = palette.index(block(WATER, level="0"))
    rock = palette.index(block("minecraft:stone"))
    dirt = palette.index(block("minecraft:dirt"))
    grass = palette.index(block("minecraft:grass_block", snowy="false"))
    sand_id = palette.index(block("minecraft:sand"))
    mud_id = palette.index(block("minecraft:mud"))
    gravel = palette.index(block("minecraft:gravel"))
    change_height = planned & (target != original_floor)
    removed = (LEVELS > target) & (LEVELS <= original_floor) & change_height
    effective[removed] = air
    raised = (LEVELS > original_floor) & (LEVELS <= target) & change_height
    effective[raised] = rock
    # Flood the new contour to a single water level. Use only dry vegetation
    # from the original column at its original Y, and leave intact trees in place.
    above = LEVELS > target
    aquatic = np.isin(names, list(AQUATIC))
    natural = np.array([natural_surface(name) for name in names])
    dry_vegetation = np.char.endswith(names, "_leaves") | np.char.endswith(names, "_log") | np.char.endswith(names, "_wood")
    dry_vegetation |= (natural & ~aquatic & (names != WATER)
                       & ~np.array([is_natural_ground(name) for name in names])
                       & ~np.isin(names, list(AIR_BLOCKS | MODDED_GROUND)))
    keep_vegetation = dry_vegetation[pristine] & (target >= original_floor) & (target >= sea + 1)
    clear = above & (LEVELS > sea) & change_height
    effective[clear] = air
    np.copyto(effective, pristine, where=(clear & keep_vegetation))
    effective[above & (LEVELS <= sea) & change_height] = water
    bed = np.where(mud > np.maximum(sand, 0.12), mud_id, np.where(sand > 0.16, sand_id, gravel))
    shore = np.where(sand > 0.14, sand_id, np.where(mud > 0.1, mud_id, grass))
    cap = np.where(target > sea, shore, bed)
    old_top = names[pristine[original_floor - MIN_Y, CELLS]]
    dry_native = np.array([is_natural_ground(name) and name not in DEEP_BED for name in old_top])
    cap = np.where((target >= sea + 2) & (original_floor >= sea + 2) & dry_native,
                   pristine[original_floor - MIN_Y, CELLS], cap)
    topsoil = (LEVELS > target - 3) & (LEVELS <= target) & change_height
    np.copyto(effective, np.where((target >= sea + 2) | (cap == grass), dirt, cap), where=topsoil)
    effective[target[change_height] - MIN_Y, CELLS[change_height]] = cap[change_height]

    # Protect all player edits, block entities and surviving structure pieces.
    # Ticking water, kelp and leaf distances can change after the earlier repair.
    # Only allow those changes to be replaced where the old operation changed
    # terrain or where water escaped above sea level beside that terrain.
    size = len(palette.states)
    timed = np.array([name in TIMED_NATURE for name in names] + [False] * (size - len(names)))
    leaves = np.array([name.endswith("_leaves") for name in names] + [False] * (size - len(names)))
    flood = (names == WATER) | aquatic
    above_sea_flood = np.pad(flood, (0, size - len(flood)), constant_values=False)
    spilled = (LEVELS > sea) & (above_sea_flood[active] | above_sea_flood[previous])
    transitional = timed[active] & timed[previous] & (
        (previous != pristine) | spilled)
    transient = transitional | (leaves[active] & leaves[previous] & (previous != pristine))
    edit_mask = (previous != pristine) | (effective != pristine) | (transient & spilled)
    different = (effective != active) & edit_mask & planned
    forbidden = np.any(different & (active != previous) & ~transient, axis=0)
    for obj in current.get("block_entities", ()):
        col = (int(obj["z"]) % 16) * 16 + int(obj["x"]) % 16
        y = int(obj["y"]) - MIN_Y
        if 0 <= y < HEIGHT and different[y, col]:
            forbidden[col] = True
    x = int(current["xPos"]) * 16 + (CELLS & 15)
    z = int(current["zPos"]) * 16 + (CELLS >> 4)
    for x0, y0, z0, x1, y1, z1 in boxes:
        footprint = (x >= x0) & (x <= x1) & (z >= z0) & (z <= z1)
        forbidden |= footprint & np.any(different & (LEVELS >= y0 - 2) & (LEVELS <= y1 + 1), axis=0)
    allowed = planned & ~forbidden
    result = np.where(allowed & edit_mask, effective, active)
    changed = (result != active).any(axis=0)
    tally["protected_columns"] += int(np.count_nonzero(forbidden & planned))
    tally["seabed_columns_lowered"] += int(np.count_nonzero(changed & seabed))
    if not changed.any():
        return False
    tally["changed_columns"] += int(changed.sum())
    tally["above_water_plants_removed"] += int(np.count_nonzero(
        np.isin(active, np.flatnonzero(np.r_[aquatic, [False] * (size - len(aquatic))]))
        & (LEVELS > sea) & (active != result)))
    pristine_sections = {int(section["Y"]): section for section in before["sections"]}
    published_sections = {int(section["Y"]): section for section in published["sections"]}
    current.pop("isLightOn", None)
    for section in current["sections"]:
        level = int(section["Y"])
        offset = level * 16 - MIN_Y
        if 0 <= offset < HEIGHT:
            section["block_states"] = palette.encode(result[offset:offset + 16].ravel(), 4)
            original = pristine_sections.get(level, {})
            prior = published_sections.get(level, {})
            if all("biomes" in layer for layer in (original, prior, section)):
                biomes = Palette(nbtlib.String, keyed=False)
                base, deployed, live = (biomes.decode(layer["biomes"], 64, 1).reshape(4, 16)
                                         for layer in (original, prior, section))
                cells = changed.reshape(4, 4, 4, 4).any(axis=(1, 3)).ravel()
                restore = cells & (live == deployed)
                if np.any(restore & (live != base)):
                    live[restore] = base[restore]
                    section["biomes"] = biomes.encode(live.ravel(), 1)
        section.pop("SkyLight", None)
        section.pop("BlockLight", None)
    for key in ("block_ticks", "fluid_ticks"):
        if key in current:
            def retain_tick(tick):
                y = int(tick["y"]) - MIN_Y
                col = (int(tick["z"]) % 16) * 16 + int(tick["x"]) % 16
                return (not 0 <= y < HEIGHT or result[y, col] == active[y, col]
                        or tick["i"] not in NATURAL_TICKS)
            current[key] = nbtlib.List[nbtlib.Compound](tick for tick in current[key] if retain_tick(tick))

    occupied = ~np.isin(result, [i for i, state in enumerate(palette.states) if state["Name"] in AIR_BLOCKS])
    actual_floor = ground(result, palette, np.full(256, MIN_Y + HEIGHT - 1))
    surface = MIN_Y + HEIGHT - np.argmax(occupied[::-1], axis=0)
    new_maps = heights(current)
    for key in HEIGHTMAPS:
        replacement = surface if key in ("WORLD_SURFACE", "MOTION_BLOCKING") else actual_floor + 1
        if key == "MOTION_BLOCKING_NO_LEAVES":
            replacement = np.maximum(replacement, np.minimum(surface, sea + 1))
        exact_original = changed & np.all(result == pristine, axis=0)
        new_maps[key][changed] = replacement[changed]
        new_maps[key][exact_original] = base_maps[key][exact_original]
        current["Heightmaps"][key] = pack(new_maps[key] - MIN_Y, 9)
    return True


def run(before, published, current, output, scope, config):
    affected = {tuple(pair) for pair in json.loads(scope.read_text())["changed_chunks"]}
    sea = config["sea_surface"]
    boxes = structure_boxes(current)
    summary = Counter()
    changed = []
    writer = Writer(current, output)
    for rx, rz in config["regions"]:
        target, mud, sand, seabed = terrain_field(
            before, published, (rx, rz), affected, sea,
            config.get("discarded_structure_footprints", ()), config.get("seabed_review", ())
        )
        for cx, cz in sorted(affected):
            if (cx // 32, cz // 32) != (rx, rz):
                continue
            a, b, c = (read_chunk(path, cx, cz) for path in (before, published, current))
            if any(chunk is None for chunk in (a, b, c)):
                raise ValueError(f"Missing complete world data for chunk ({cx}, {cz})")
            nearby = boxes(c)
            if nearby is None:
                summary["unresolved_structure_chunks"] += 1
                continue
            x, z = (cx % 32) * 16 + PAD, (cz % 32) * 16 + PAD
            slot = np.s_[z:z + 16, x:x + 16]
            if rework(a, b, c, target[slot].ravel(), mud[slot].ravel(), sand[slot].ravel(), seabed[slot].ravel(),
                      sea, nearby, summary):
                writer.write(cx, cz, c)
                changed.append((cx, cz))
    writer.flush()
    return {"changed_chunks": changed, **summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("before", "published", "current", "output", "scope", "config"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    config = json.loads(args.config.read_text())
    results = run(args.before, args.published, args.current, args.output, args.scope, config)
    (args.output / "report.json").write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({key: len(value) if key == "changed_chunks" else value for key, value in results.items()}))


if __name__ == "__main__":
    main()
