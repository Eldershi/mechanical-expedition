#!/usr/bin/env python3
"""Blend generated terrain into adjacent retained terrain in a closed world copy."""

import argparse
from collections import Counter
from functools import lru_cache
import json
from pathlib import Path

import nbtlib
import numpy as np

from measure_chunk_edges import read_chunk
from splice_overworld_island import (
    AIR, CELLS, HEIGHT, HEIGHTMAPS, LEVELS, MIN_Y, Palette, Writer,
    arrays, block, heights, is_natural_ground, natural_floor, pack, smooth,
)


AIR_BLOCKS = {AIR, "minecraft:cave_air", "minecraft:void_air"}
WATER = "minecraft:water"
NATURAL_DETAIL = {
    "short_grass", "tall_grass", "fern", "large_fern", "dead_bush",
    "dandelion", "poppy", "brown_mushroom", "red_mushroom", "vine", "lily_pad",
    "kelp", "kelp_plant", "seagrass", "tall_seagrass", "snow", "powder_snow",
}
TREE_PARTS = ("_leaves", "_log", "_wood")
MODDED_GROUND = {
    "quark:limestone", "quark:shale", "quark:jasper",
    "biomeswevegone:overgrown_dacite", "biomeswevegone:dacite",
    "supplementaries:barnacles", "spawn:reefstone", "spawn:sea_urchin", "spawn:sea_star",
}
LEGACY_SUBSTRATES = {"cmi:peat_block", "terramity:igneostone"}
NATURAL_TICKS = {"minecraft:gravel", "minecraft:sand", "minecraft:water", "minecraft:flowing_water"}
SEA_DECORATIONS = {"spawn:sea_star", "spawn:sea_urchin"}


def natural_surface(identifier):
    namespace, name = identifier.split(":", 1)
    return (
        is_natural_ground(identifier)
        or identifier in MODDED_GROUND
        or name.endswith("_ore")
        or identifier in AIR_BLOCKS
        or namespace == "minecraft" and (name == "water" or name in NATURAL_DETAIL)
        or namespace in {"minecraft", "biomesoplenty", "biomeswevegone", "regions_unexplored"}
        and name.endswith(TREE_PARTS)
    )


def local_distance(cx, cz, retained, radius):
    x = cx * 16 + (CELLS & 15)
    z = cz * 16 + (CELLS >> 4)
    distance = np.full(256, float(radius))
    reach = (radius + 15) // 16
    for ox in range(cx - reach, cx + reach + 1):
        for oz in range(cz - reach, cz + reach + 1):
            if not retained(ox, oz):
                continue
            dx = np.maximum(0, np.maximum(ox * 16 - x, x - (ox * 16 + 15)))
            dz = np.maximum(0, np.maximum(oz * 16 - z, z - (oz * 16 + 15)))
            distance = np.minimum(distance, np.hypot(dx, dz))
    return distance


def region_chunks(region):
    rx, rz = region
    return ((rx * 32 + x, rz * 32 + z) for z in range(32) for x in range(32))


def protected_columns(chunk, floor_band, structures):
    result = np.zeros(256, dtype=bool)
    for key in ("block_entities", "block_ticks", "fluid_ticks"):
        for entry in chunk.get(key, ()):
            column = ((int(entry["z"]) % 16) * 16) + int(entry["x"]) % 16
            if entry.get("i") in NATURAL_TICKS or entry.get("id") in SEA_DECORATIONS:
                continue
            if int(entry["y"]) >= floor_band[column]:
                result[column] = True
    x = int(chunk["xPos"]) * 16 + (CELLS & 15)
    z = int(chunk["zPos"]) * 16 + (CELLS >> 4)
    for x0, _, z0, x1, y1, z1 in structures:
        result |= (x >= x0) & (x <= x1) & (z >= z0) & (z <= z1) & (floor_band <= y1)
    return result


def repair_chunk(live, legacy, distance, radius, sea, biome_names, structures):
    palette = Palette(nbtlib.Compound, keyed=True)
    current = arrays(live, palette)
    original = arrays(legacy, palette)
    for index, state in enumerate(tuple(palette.states)):
        if state["Name"] == "minecraft:grass":
            original[original == index] = palette.index(block("minecraft:short_grass"))
    live_height, legacy_height = heights(live), heights(legacy)
    live_floor = natural_floor(current, palette, live_height["OCEAN_FLOOR"] - 1)
    legacy_ceiling = legacy_height["OCEAN_FLOOR"] - 1
    legacy_floor = natural_floor(original, palette, legacy_ceiling)
    extra_ground = [i for i, s in enumerate(palette.states)
                    if s["Name"] in (MODDED_GROUND | LEGACY_SUBSTRATES) - SEA_DECORATIONS]
    old_rock = np.isin(original, extra_ground) & (LEVELS <= legacy_ceiling)
    old_rock_y = np.where(old_rock.any(axis=0), MIN_Y + HEIGHT - 1 - np.argmax(old_rock[::-1], axis=0), MIN_Y)
    legacy_floor = np.maximum(legacy_floor, old_rock_y)
    weight = 1 - smooth((distance - 1) / (radius - 1))
    new_floor = np.rint(live_floor + (legacy_floor - live_floor) * weight).astype(int)

    names = np.array([str(state["Name"]) for state in palette.states])
    safe = np.array([natural_surface(name) for name in names])
    floor_band = np.minimum(live_floor, new_floor) - 3
    volume = LEVELS >= floor_band
    protected = protected_columns(live, floor_band, structures) | np.any(volume & ~safe[current], axis=0)
    changed = (weight > 0) & (new_floor != live_floor) & ~protected
    if not changed.any():
        return None, int(protected.sum())

    result = current.copy()
    air = palette.index(block(AIR))
    water = palette.index(block(WATER, level="0"))
    stone = palette.index(block("minecraft:stone"))
    deepslate = palette.index(block("minecraft:deepslate", axis="y"))
    sand = palette.index(block("minecraft:sand"))
    mud = palette.index(block("minecraft:mud"))
    gravel = palette.index(block("minecraft:gravel"))
    dirt = palette.index(block("minecraft:dirt"))
    grass = palette.index(block("minecraft:grass_block", snowy="false"))
    result[(LEVELS > new_floor) & changed] = air
    result[(LEVELS > new_floor) & (LEVELS <= sea) & changed] = water
    added = (LEVELS > live_floor) & (LEVELS <= new_floor) & changed
    result[added & (LEVELS >= 0)] = stone
    result[added & (LEVELS < 0)] = deepslate

    # Follow the original soil and bank profile near the retained edge.
    columns = np.arange(256)
    legacy_top = original[np.clip(legacy_floor - MIN_Y, 0, HEIGHT - 1), columns]
    legacy_top_names = names[legacy_top]
    underwater = np.where(np.char.endswith(legacy_top_names, ":mud"), mud, gravel)
    cap = np.where(new_floor < sea - 3, underwater, np.where(new_floor <= sea + 1, sand, grass))
    legacy_soil = np.array([is_natural_ground(name) for name in names])[legacy_top]
    cap = np.where((weight >= 0.8) & legacy_soil, legacy_top, cap)
    cap = np.where((weight >= 0.8) & (legacy_top_names == "cmi:peat_block"), mud, cap)
    cover = (LEVELS > new_floor - 3) & (LEVELS <= new_floor) & changed
    soil = np.where(new_floor <= sea + 1, np.where(cap == mud, mud, sand), dirt)
    np.copyto(result, soil, where=cover)
    result[new_floor[changed] - MIN_Y, columns[changed]] = cap[changed]

    # Carry the existing or legacy vegetation up to its new natural ground.
    for column in columns[changed & (new_floor > sea)]:
        use_legacy = weight[column] >= 0.85
        origin = original if use_legacy else current
        floor = legacy_floor[column] if use_legacy else live_floor[column]
        offsets = np.arange(1, min(48, MIN_Y + HEIGHT - 1 - max(floor, new_floor[column])) + 1)
        decorations = origin[floor + offsets - MIN_Y, column]
        carry = np.array([
            names[v].startswith("minecraft:")
            and (names[v].split(":", 1)[1] in NATURAL_DETAIL or names[v].endswith(TREE_PARTS))
            or names[v] in {"biomeswevegone:holly_log", "biomeswevegone:holly_leaves"}
            for v in decorations
        ], dtype=bool)
        result[new_floor[column] + offsets[carry] - MIN_Y, column] = decorations[carry]

    for key in ("block_entities", "block_ticks", "fluid_ticks"):
        entries = live.get(key)
        if entries is None:
            continue
        kept = []
        for entry in entries:
            col = (int(entry["z"]) % 16) * 16 + int(entry["x"]) % 16
            y = int(entry["y"]) - MIN_Y
            natural = entry.get("i") in NATURAL_TICKS or entry.get("id") in SEA_DECORATIONS
            if natural and 0 <= y < HEIGHT and result[y, col] != current[y, col]:
                continue
            kept.append(entry)
        live[key] = nbtlib.List[nbtlib.Compound](kept)

    old_sections = {int(section["Y"]): section for section in legacy["sections"]}
    biome_columns = (np.arange(4)[:, None] * 64 + (np.arange(4) * 4)[None, :] + 34).ravel()
    carry_biome = changed[biome_columns] & (weight[biome_columns] >= 0.6)
    for section in live["sections"]:
        offset = int(section["Y"]) * 16 - MIN_Y
        if not 0 <= offset < HEIGHT:
            continue
        section["block_states"] = palette.encode(result[offset:offset + 16].ravel(), 4)
        old = old_sections.get(int(section["Y"]))
        if carry_biome.any() and old and "biomes" in old and "biomes" in section:
            biomes = Palette(nbtlib.String, keyed=False)
            live_ids = biomes.decode(section["biomes"], 64, 1).reshape(4, 16)
            legacy_ids = biomes.decode(old["biomes"], 64, 1).reshape(4, 16)
            supported = np.isin(legacy_ids, [i for i, name in enumerate(biomes.states) if name in biome_names])
            mask = carry_biome & supported
            live_ids[mask] = legacy_ids[mask]
            section["biomes"] = biomes.encode(live_ids.ravel(), 1)
        section.pop("SkyLight", None)
        section.pop("BlockLight", None)
    live.pop("isLightOn", None)
    occupied = ~np.isin(result, [i for i, state in enumerate(palette.states) if state["Name"] in AIR_BLOCKS])
    surface = MIN_Y + HEIGHT - np.argmax(occupied[::-1], axis=0)
    for name in HEIGHTMAPS:
        values = live_height[name]
        height = new_floor + 1 if name == "OCEAN_FLOOR" else np.maximum(sea, new_floor) + 1
        values[changed] = (surface if name == "WORLD_SURFACE" else height)[changed]
        live["Heightmaps"][name] = pack(values - MIN_Y, 9)
    return live, int(protected.sum())


def run(live, retained_world, legacy, output, regions, radius, sea, biome_names):
    @lru_cache(maxsize=None)
    def retained(cx, cz):
        path = retained_world / f"r.{cx // 32}.{cz // 32}.mca"
        if not path.is_file():
            return False
        with path.open("rb") as stream:
            stream.seek(4 * ((cx % 32) + 32 * (cz % 32)))
            if not int.from_bytes(stream.read(3), "big"):
                return False
        return read_chunk(retained_world, cx, cz) is not None

    @lru_cache(maxsize=128)
    def structure_starts(cx, cz):
        chunk = read_chunk(live, cx, cz, full=False)
        return chunk.get("structures", {}).get("starts", {}) if chunk is not None else {}

    def signed(value):
        value &= 0xFFFFFFFF
        return value - 0x100000000 if value & 0x80000000 else value

    def boxes(chunk):
        structures = chunk.get("structures", {})
        starts = list(structures.get("starts", {}).values())
        for key, references in structures.get("References", {}).items():
            for position in references:
                start = structure_starts(signed(int(position)), signed(int(position) >> 32)).get(key)
                if start is None:
                    return None
                starts.append(start)
        return [tuple(map(int, piece["BB"])) for start in starts for piece in start.get("Children", ())
                if "BB" in piece and len(piece["BB"]) == 6]

    writer = Writer(live, output)
    affected = []
    summary = Counter()
    for region in sorted(regions):
        for cx, cz in region_chunks(region):
            if retained(cx, cz):
                continue
            distance = local_distance(cx, cz, retained, radius)
            if np.all(distance >= radius):
                continue
            chunk = read_chunk(live, cx, cz)
            if chunk is None:
                summary["unavailable_live_chunks"] += 1
                continue
            original = read_chunk(legacy, cx, cz)
            if original is None:
                summary["unavailable_legacy_chunks"] += 1
                continue
            structure_boxes = boxes(chunk)
            if structure_boxes is None:
                summary["unresolved_structure_chunks"] += 1
                continue
            updated, protected = repair_chunk(
                chunk, original, distance, radius, sea, biome_names, structure_boxes
            )
            summary["protected_columns"] += protected
            if updated is not None:
                writer.write(cx, cz, updated)
                affected.append((cx, cz))
    writer.flush()
    return {"changed_chunks": affected, **summary}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("live", "retained", "legacy", "output", "config"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    radius = config.get("radius", 128)
    if radius < 16:
        parser.error("The transition must be at least one chunk wide")
    args.output.mkdir(parents=True, exist_ok=False)
    report = run(args.live, args.retained, args.legacy, args.output,
                 [tuple(region) for region in config["regions"]], radius,
                 config.get("sea_level", 63) - 1, set(config["biomes"]))
    (args.output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Rewrote {len(report['changed_chunks'])} chunks in the output directory")


if __name__ == "__main__":
    main()
