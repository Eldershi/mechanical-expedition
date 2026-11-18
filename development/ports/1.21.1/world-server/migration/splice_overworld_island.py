#!/usr/bin/env python3
"""Splice an upgraded island and protected structures into a fresh Overworld offline."""

import argparse
from collections import Counter, defaultdict
from functools import lru_cache
import json
from pathlib import Path
import shutil
import tempfile

import nbtlib
import numpy as np

from measure_chunk_edges import read_chunk
from prepare_region_copy import replace_chunk


MIN_Y = -64
HEIGHT = 384
DATA_VERSION = 3955
SECTOR = 4096
AIR = "minecraft:air"
HEIGHTMAPS = ("WORLD_SURFACE", "OCEAN_FLOOR", "MOTION_BLOCKING", "MOTION_BLOCKING_NO_LEAVES")
CELLS = np.arange(256)
LEVELS = np.arange(MIN_Y, MIN_Y + HEIGHT)[:, None]
SOIL_AND_ROCK = frozenset((
    "andesite", "basalt", "bedrock", "blackstone", "calcite", "clay", "coarse_dirt", "deepslate",
    "diorite", "dirt", "dripstone_block", "end_stone", "granite", "grass_block", "gravel",
    "ice", "moss_block", "mud", "mycelium", "netherrack", "obsidian", "packed_ice", "podzol",
    "red_sand", "red_sandstone", "rooted_dirt", "sand", "sandstone", "smooth_basalt", "snow_block",
    "stone", "terracotta", "tuff",
))
NATURAL_VARIANTS = ("_sand", "_sandstone", "_grass_block", "_dirt", "_gravel", "_podzol", "_clay", "_terracotta")


def packed_values(data, count, bits):
    indices = np.arange(count, dtype=np.uint64)
    per_long = 64 // bits
    longs = np.asarray(data, dtype=np.int64).view(np.uint64)
    return ((longs[indices // per_long] >> (indices % per_long * bits)) & ((1 << bits) - 1)).astype(np.int32)


def pack(values, bits):
    indices = np.arange(values.size, dtype=np.uint64)
    per_long = 64 // bits
    words = np.zeros((values.size + per_long - 1) // per_long, dtype=np.uint64)
    np.bitwise_or.at(words, indices // per_long, values.astype(np.uint64) << (indices % per_long * bits))
    return nbtlib.LongArray(words.view(np.int64))


class Palette:
    def __init__(self, types, keyed):
        self.types = types
        self.keyed = keyed
        self.states = []
        self.ids = {}

    def index(self, state):
        key = (str(state["Name"]), tuple(sorted(state.get("Properties", {}).items()))) if self.keyed else str(state)
        if key not in self.ids:
            self.ids[key] = len(self.states)
            self.states.append(state)
        return self.ids[key]

    def decode(self, data, count, minimum_bits):
        ids = np.asarray([self.index(state) for state in data["palette"]], dtype=np.int32)
        if len(ids) == 1:
            return np.full(count, ids[0], dtype=np.int32)
        bits = max(minimum_bits, (len(ids) - 1).bit_length())
        return ids[packed_values(data["data"], count, bits)]

    def encode(self, states, minimum_bits):
        unique, indexes = np.unique(states, return_inverse=True)
        encoded = nbtlib.Compound({"palette": nbtlib.List[self.types](self.states[ident] for ident in unique)})
        if len(unique) > 1:
            bits = max(minimum_bits, (len(unique) - 1).bit_length())
            encoded["data"] = pack(indexes, bits)
        return encoded


def block(name, **properties):
    state = nbtlib.Compound({"Name": nbtlib.String(name)})
    if properties:
        state["Properties"] = nbtlib.Compound({key: nbtlib.String(value) for key, value in properties.items()})
    return state


def arrays(chunk, palette):
    states = np.full((HEIGHT, 256), palette.index(block(AIR)), dtype=np.int32)
    for section in chunk["sections"]:
        offset = int(section["Y"]) * 16 - MIN_Y
        if 0 <= offset < HEIGHT and "block_states" in section:
            states[offset:offset + 16] = palette.decode(section["block_states"], 4096, 4).reshape(16, 256)
    return states


def heights(chunk):
    return {name: packed_values(chunk["Heightmaps"][name], 256, 9) + MIN_Y for name in HEIGHTMAPS}


def is_natural_ground(identifier):
    namespace, name = identifier.split(":", 1)
    if namespace == "minecraft":
        return name in SOIL_AND_ROCK or name.endswith(("_terracotta", "_ore")) and "_glazed_" not in name
    return namespace in {"biomesoplenty", "biomeswevegone", "wythers", "terralith"} and (
        name in SOIL_AND_ROCK or name.endswith(NATURAL_VARIANTS)
    )


def natural_floor(states, palette, heightmap):
    soil = [i for i, state in enumerate(palette.states) if is_natural_ground(state["Name"])]
    solid = np.isin(states, soil) & (LEVELS <= heightmap)
    return np.where(solid.any(axis=0), MIN_Y + HEIGHT - 1 - np.argmax(solid[::-1], axis=0), heightmap)


def inside_box(box, x, z):
    x0, _, z0, x1, _, z1 = box
    return (x >= x0) & (x <= x1) & (z >= z0) & (z <= z1)


def distances(x, z, core, radius):
    x0, z0, x1, z1 = core
    rx = np.clip(x, x0 + radius, x1 - radius)
    rz = np.clip(z, z0 + radius, z1 - radius)
    dx = x - rx
    dz = z - rz
    d = np.hypot(dx, dz)
    scale = np.minimum(1, radius / np.maximum(1, d))
    return d - radius, np.rint(rx + dx * scale).astype(int), np.rint(rz + dz * scale).astype(int)


def smooth(t):
    t = np.clip(t, 0, 1)
    return t * t * t * (t * (t * 6 - 15) + 10)


def validate(config):
    core = tuple(config["core"])
    x0, z0, x1, z1 = core
    radius = config.get("corner_radius", 0)
    inner, belt, outer = (config["widths"][name] for name in ("inner", "water", "outer"))
    sea_y = config.get("sea_level", 63) - 1
    depth = config.get("sea_depth", 24)
    if not (0 <= radius <= min(x1 - x0, z1 - z0) / 2 and min(inner, belt, outer) >= 16):
        raise ValueError("Invalid core geometry or band width")
    if not MIN_Y + 4 < sea_y - depth < sea_y - 5 < MIN_Y + HEIGHT - 1:
        raise ValueError("Invalid sea level or sea depth")
    boxes = []
    for route in config.get("protected_structures", []):
        names = frozenset(route["blocks"])
        if not names or names & {AIR, "minecraft:cave_air", "minecraft:void_air", "minecraft:water"}:
            raise ValueError("Protected structures require their explicit block IDs without air or water")
        for box in map(tuple, route["boxes"]):
            if any(a > b for a, b in zip(box[:3], box[3:], strict=True)) or not MIN_Y <= box[1] <= box[4] < MIN_Y + HEIGHT:
                raise ValueError(f"Invalid protected volume {box}")
            boxes.append((box, names))
    return core, radius, inner, belt, outer, sea_y, depth, boxes


def choose_chunks(core, reach, boxes):
    x0, z0, x1, z1 = core
    chunks = {(x,z) for z in range((z0 - reach)//16, (z1 + reach)//16 + 1)
              for x in range((x0 - reach)//16, (x1 + reach)//16 + 1)}
    protected = defaultdict(list)
    for entry in boxes:
        x0, _, z0, x1, _, z1 = entry[0]
        for z in range(z0 // 16, z1 // 16 + 1):
            for x in range(x0 // 16, x1 // 16 + 1):
                protected[x, z].append(entry)
    chunks.update(protected)
    ordered = sorted(chunks, key=lambda coord: (coord[0]//32, coord[1]//32, coord[1], coord[0]))
    return ordered, protected


def choose_tiles(source, target, take_old, take_target):
    return nbtlib.List[nbtlib.Compound](
        tile for items, keep in ((source, take_old), (target, take_target))
        for tile in items
        if keep(int(tile["x"]) % 16, int(tile["y"]), int(tile["z"]) % 16)
    )


def copy_biomes(section, old_section, distance, cut, blend_old):
    if "biomes" not in section:
        return
    biome_palette = Palette(nbtlib.String, keyed=False)
    values = biome_palette.decode(section["biomes"], 64, 1).reshape(4, 16)
    if old_section is not None and "biomes" in old_section and blend_old.any():
        source = biome_palette.decode(old_section["biomes"], 64, 1).reshape(4, 16)
        values[:, blend_old] = source[:, blend_old]
    sea = (distance > 0) & (distance < cut)
    values[:, sea] = biome_palette.index(nbtlib.String("minecraft:ocean"))
    section["biomes"] = biome_palette.encode(values.ravel(), 1)


def mix(source, target, x, z, d, nearest_x, nearest_z, bands, protected, old_floor, counts):
    inner, belt, outer, sea_y, depth = bands
    reach = inner + belt + outer
    core = d <= 0
    changed = (d > 0) & (d < reach)
    chunk_pos = (x[0] // 16, z[0] // 16)
    if source is not None and int(source["DataVersion"]) != DATA_VERSION and core.any():
        raise ValueError(f"Upgrade mixed source chunk {chunk_pos} before splicing")
    palette = Palette(nbtlib.Compound, keyed=True)
    air = palette.index(block(AIR))
    water = palette.index(block("minecraft:water", level="0"))
    stone = palette.index(block("minecraft:stone"))
    deepslate = palette.index(block("minecraft:deepslate", axis="y"))
    sand = palette.index(block("minecraft:sand"))
    gravel = palette.index(block("minecraft:gravel"))
    dirt = palette.index(block("minecraft:dirt"))
    grass = palette.index(block("minecraft:grass_block", snowy="false"))
    values = arrays(target, palette)
    before = heights(target)
    floor_heightmap = before["OCEAN_FLOOR"] - 1
    ground = natural_floor(values, palette, floor_heightmap)
    counts["ignored_cover_columns"] += int(np.count_nonzero(changed & (ground != floor_heightmap)))
    ocean = sea_y - depth + np.sin(x * 0.019) * 1.35 + np.cos(z * 0.023) * 1.35
    coastal = np.array([old_floor(a, b) for a, b in zip(nearest_x, nearest_z, strict=True)] if
                       np.any(changed & (d < inner)) else ocean)
    relief = np.where(d < inner, coastal + (ocean - coastal) * smooth(d / inner),
                      ocean + (ground - ocean) * smooth((d - inner - belt) / outer))
    cap = np.rint(relief).astype(np.int32)
    cap = np.clip(cap, MIN_Y + 4, MIN_Y + HEIGHT - 1)
    # Leave vegetation and other features intact on the fresh side where the slope reaches their original ground.
    changed &= ~((d > inner + belt + outer * 0.65) & (cap == ground))
    # Cut to the new ground and keep existing subsurface where possible.
    values[(LEVELS > cap) & changed] = air
    values[(LEVELS > cap) & (LEVELS <= sea_y) & changed] = water
    added_mass = (LEVELS > ground) & (LEVELS <= cap) & changed
    values[added_mass & (LEVELS >= 0)] = stone
    values[added_mass & (LEVELS < 0)] = deepslate
    cover = (LEVELS > cap - 3) & (LEVELS <= cap) & changed
    values[cover & (cap <= sea_y - 5)] = gravel
    values[cover & (cap > sea_y - 5) & (cap <= sea_y + 2)] = sand
    values[cover & (cap > sea_y + 2)] = dirt
    values[(LEVELS == cap) & changed & (cap > sea_y + 2)] = grass

    old_sections = {}
    old_tiles = np.zeros((HEIGHT, 256), dtype=bool)
    if source is not None:
        old_values = arrays(source, palette)
        source_heights = heights(source)
        old_tiles[:, core] = True
        old_sections = {int(s["Y"]): s for s in source["sections"]}
        for box, allowed in protected:
            eligible = inside_box(box, x, z)
            indices = [i for i, state in enumerate(palette.states) if state["Name"] in allowed]
            old_tiles |= eligible & (LEVELS >= box[1]) & (LEVELS <= box[4]) & np.isin(old_values, indices)
        if int(source["DataVersion"]) != DATA_VERSION and old_tiles.any():
            raise ValueError(f"Upgrade protected source chunk {chunk_pos} before splicing")
        values[old_tiles] = old_values[old_tiles]
        counts["protected_voxels"] += int(np.count_nonzero(old_tiles[:, ~core]))

    keep_old = lambda lx, y, lz: MIN_Y <= y < MIN_Y + HEIGHT and old_tiles[y - MIN_Y, lx + 16*lz]
    keep_new = lambda lx, y, lz: not core[lx + 16*lz] and not changed[lx + 16*lz] and not keep_old(lx,y,lz)
    for key in ("block_entities", "block_ticks", "fluid_ticks"):
        target[key] = choose_tiles(source.get(key, ()) if source is not None else (),
                                   target.get(key, ()), keep_old, keep_new)
    target.pop("isLightOn", None)
    target.pop("structures", None)
    if "PostProcessing" in target:
        post = target["PostProcessing"]
        source_post = source.get("PostProcessing", ()) if source is not None else ()
        for layer in range(len(post)):
            def keeps(packed, keep):
                return keep(int(packed) & 15, MIN_Y + layer * 16 + (int(packed) >> 4 & 15), int(packed) >> 8 & 15)
            old = (p for p in source_post[layer] if keeps(p, keep_old)) if layer < len(source_post) else ()
            post[layer] = nbtlib.List[nbtlib.Short]([*old, *(p for p in post[layer] if keeps(p, keep_new))])

    biome_columns = (np.arange(4)[:, None] * 64 + (np.arange(4) * 4)[None, :] + 34).ravel()
    for section in target["sections"]:
        section.pop("SkyLight", None)
        section.pop("BlockLight", None)
        sy = int(section["Y"])
        offset = sy * 16 - MIN_Y
        if not 0 <= offset < HEIGHT:
            continue
        section["block_states"] = palette.encode(values[offset:offset+16].ravel(), 4)
        blend_old = core[biome_columns]
        copy_biomes(section, old_sections.get(sy), d[biome_columns], inner + belt + outer * 0.5, blend_old)

    is_air = np.isin(values, [i for i, state in enumerate(palette.states)
                            if state["Name"] in {AIR, "minecraft:cave_air", "minecraft:void_air"}])
    is_water = values == water
    upper = np.where(is_air.all(axis=0), MIN_Y, MIN_Y + HEIGHT - np.argmax(~is_air[::-1], axis=0))
    overlay = old_tiles & ~is_air & ~is_water & ~core
    overlay_height = np.where(overlay, LEVELS + 1, MIN_Y).max(axis=0)
    for key in HEIGHTMAPS:
        heights_out = before[key].copy()
        synthetic = cap + 1
        if key != "OCEAN_FLOOR":
            synthetic = np.maximum(synthetic, sea_y + 1)
        if key == "WORLD_SURFACE":
            synthetic = upper
        heights_out[changed] = synthetic[changed]
        heights_out[~core] = np.maximum(heights_out[~core], overlay_height[~core])
        if source is not None:
            heights_out[core] = source_heights[key][core]
        target["Heightmaps"][key] = pack(heights_out - MIN_Y, 9)

    ring = (d >= inner) & (d < inner + belt)
    exposed = ring & np.any((LEVELS > sea_y) & ~is_air & ~old_tiles, axis=0)
    if exposed.any():
        raise ValueError(f"Exposed terrain inside water band at {x[exposed][0]}, {z[exposed][0]}")
    surface_water = is_water[sea_y - MIN_Y]
    if np.any(ring & ~surface_water & ~old_tiles[sea_y - MIN_Y]):
        raise ValueError("Water band contains a non-water surface outside the protected structures")
    counts["water_band_columns"] += int(ring.sum())
    counts["water_band_water_surface"] += int((ring & surface_water).sum())
    counts["transferred_block_entities"] += sum(
        bool(keep_old(int(tile["x"]) % 16, int(tile["y"]), int(tile["z"]) % 16))
        for tile in target["block_entities"]
    )
    return target


class Writer:
    def __init__(self, target, output):
        self.target = target
        self.output = output
        self.name = None
        self.data = None

    def write(self, x, z, chunk):
        name = f"r.{x//32}.{z//32}.mca"
        if name != self.name:
            self.flush()
            self.name = name
            self.data = bytearray((self.target / name).read_bytes())
        entry = ((x % 32) + 32 * (z % 32)) * 4
        offset = int.from_bytes(self.data[entry:entry+3], "big") * SECTOR
        replace_chunk(self.data, entry, offset, self.data[entry+3], chunk)

    def flush(self):
        if self.data is not None:
            (self.output / self.name).write_bytes(self.data)
            self.data = None


def splice(source, target, output, config, structure_source=None):
    core, radius, inner, belt, outer, sea_y, depth, boxes = validate(config)
    reach = inner + belt + outer
    counts = Counter()
    source_chunks, transition_chunks = [], []
    writer = Writer(target, output)

    @lru_cache(maxsize=256)
    def saved_floor(cx, cz):
        chunk = read_chunk(source, cx, cz)
        if chunk is None:
            raise ValueError(f"Missing source elevation samples at chunk ({cx}, {cz})")
        palette = Palette(nbtlib.Compound, keyed=True)
        states = arrays(chunk, palette)
        return natural_floor(states, palette, heights(chunk)["OCEAN_FLOOR"] - 1)

    def near_floor(x, z):
        return saved_floor(x//16, z//16)[(z % 16) * 16 + x % 16]

    chunks, protected_chunks = choose_chunks(core, reach, boxes)
    for cx, cz in chunks:
        x = cx * 16 + (CELLS & 15)
        z = cz * 16 + (CELLS >> 4)
        d, nearest_x, nearest_z = distances(x, z, core, radius)
        protected = protected_chunks.get((cx, cz), ())
        if np.all(d >= reach) and not protected:
            continue
        target_chunk = read_chunk(target, cx, cz)
        if target_chunk is None or int(target_chunk["DataVersion"]) != DATA_VERSION:
            raise ValueError(f"Missing fresh FULL 1.21.1 template chunk ({cx}, {cz})")
        source_chunk = read_chunk(source, cx, cz) if np.any(d <= 0) or protected else None
        if protected and not np.any(d <= 0) and structure_source is not None and (
                source_chunk is None or int(source_chunk["DataVersion"]) != DATA_VERSION):
            upgrade = read_chunk(structure_source, cx, cz)
            if upgrade is not None and int(upgrade["DataVersion"]) == DATA_VERSION:
                source_chunk = upgrade
        if (np.any(d <= 0) or protected) and source_chunk is None:
            raise ValueError(f"Missing FULL island or structure chunk ({cx}, {cz})")
        if np.all(d <= 0):
            result = source_chunk
            counts["exact_source_chunks"] += 1
            counts["exact_source_block_entities"] += len(result.get("block_entities", ()))
            source_chunks.append((cx, cz))
        else:
            result = mix(source_chunk, target_chunk, x, z, d, nearest_x, nearest_z,
                         (inner, belt, outer, sea_y, depth), protected, near_floor, counts)
            counts["blended_chunks"] += 1
            transition_chunks.append((cx, cz))
        writer.write(cx, cz, result)
    writer.flush()
    for file in target.glob("r.*.mca"):
        if not (output / file.name).exists():
            shutil.copy2(file, output / file.name)
    rewritten = set(source_chunks) | set(transition_chunks)
    for file in target.glob("c.*.*.mcc"):
        _, cx, cz, _ = file.name.split(".")
        if (int(cx), int(cz)) not in rewritten:
            shutil.copy2(file, output / file.name)
    return dict(counts, source_chunks=source_chunks, transition_chunks=transition_chunks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-regions", required=True, type=Path)
    parser.add_argument("--structure-regions", type=Path,
                        help="Use the upgraded copy for protected structures when the source chunk is still legacy.")
    parser.add_argument("--fresh-regions", required=True, type=Path)
    parser.add_argument("--output-regions", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    source, fresh, output = (p.resolve() for p in (args.source_regions, args.fresh_regions, args.output_regions))
    structure_source = args.structure_regions.resolve() if args.structure_regions else None
    if source == fresh or any(parent == output or output in parent.parents or parent in output.parents
                              for parent in (source, fresh, structure_source) if parent is not None):
        parser.error("Use two separate saved source folders and a new output folder outside of both.")
    config = json.loads(args.config.read_text())
    if output.exists():
        parser.error(f"The output folder already exists: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix=".island-splice-", dir=output.parent) as temporary:
            working = Path(temporary) / "region"
            working.mkdir()
            report = json.dumps(splice(source, fresh, working, config, structure_source), indent=2, sort_keys=True)
            working.rename(output)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Island splice failed: {error}\n")
    print(report)


if __name__ == "__main__":
    main()
