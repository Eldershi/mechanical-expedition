#!/usr/bin/env python3
"""Apply reviewed terrain, vegetation, and container conversions to a closed world copy."""

import argparse
from collections import Counter
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import uuid

import nbtlib
import numpy as np

from audit_block_palettes import AIR, properties, region_chunks, terrain_regions
from migrate_quartz_and_peat import read_indices, write_indices
from prepare_region_copy import replace_chunk
from remap_retired_blocks import block_position

POLICY = Path(__file__).with_name("residual_block_policy.json")
QUARK_CHEST = "quark:lootr_variant_trapped_chest"
FLOWER_DATA = {
    "terramity:gaia_lily_ready": set(),
    "forbidden_arcanus:nipa": {"LastSpeck", "Players"},
}
RETIRED_ENTITY_DATA = {
    "malum:void_conduit": {"progress", "streak", "lingeringRadiance"},
    "terramity:cardboard_box": {"Items"},
    "terramity:cardboard_box_marked": {"Items", "LootTable", "LootTableSeed"},
}
ENTITY_COORDINATES = {"id", "x", "y", "z", "keepPacked", "ForgeCaps"}


def target_state(variant, old_state, catalog):
    name = variant["target"]
    attrs = properties(old_state) if variant.get("copy_properties") else {}
    attrs.update(variant.get("properties", {}))
    schema = catalog[name]["properties"]
    if attrs.keys() != schema.keys() or any(v not in schema[k] for k, v in attrs.items()):
        raise ValueError(f"Incompatible properties for {old_state['Name']} -> {name}: {attrs}")
    result = nbtlib.Compound({"Name": nbtlib.String(name)})
    if attrs:
        result["Properties"] = nbtlib.Compound({k: nbtlib.String(v) for k, v in attrs.items()})
    return result


def convert_chest(entity, world, loot_tables):
    fields = {"tileId", "LootTable", "LootTableSeed", "LootrOpeners", "ForgeData"}
    if set(entity) - ENTITY_COORDINATES - fields or entity.get("ForgeCaps") or entity.get("ForgeData"):
        raise ValueError("Quark chest has additional data that needs a separate conversion")
    old = entity.get("tileId")
    if not isinstance(old, nbtlib.IntArray) or len(old) != 4:
        raise ValueError("Quark chest has no valid old Lootr UUID")
    tile = uuid.UUID(bytes=b"".join((int(value) & 0xFFFFFFFF).to_bytes(4, "big") for value in old))
    if entity.get("LootrOpeners") or any((world / "data" / "lootr").rglob(f"{tile}.dat")):
        raise ValueError("Previously opened Lootr chest requires a separate inventory conversion")
    if entity.get("LootTable") not in loot_tables or "LootTableSeed" not in entity:
        raise ValueError(f"Unverified Quark chest loot table {entity.get('LootTable')}")
    entity["LootrId"] = entity.pop("tileId")
    entity["LootrHasBeenOpened"] = nbtlib.Byte(0)


def handle_entities(old, mode, entities, positions, world, loot_tables):
    has_data = {p: entities[p] for p in positions if p in entities}
    if not mode:
        if has_data:
            raise ValueError(f"Unexpected block entity for {old} at {next(iter(has_data))}")
        return
    if len(has_data) != len(positions):
        raise ValueError(f"Missing expected block entity for {old} at {positions[0]}")
    for position, entity in has_data.items():
        if mode == "quark_lootr_chest" and entity["id"] == QUARK_CHEST:
            convert_chest(entity, world, loot_tables)
        elif mode == "empty_plant" and entity["id"] == old and old in FLOWER_DATA:
            if set(entity) - ENTITY_COORDINATES - FLOWER_DATA[old] or entity.get("Players") or entity.get("ForgeCaps"):
                raise ValueError(f"Plant {old} at {position} has unhandled saved data")
            del entities[position]
        elif mode == "retired_entity" and entity["id"] == old and old in RETIRED_ENTITY_DATA:
            active = ("Items", "ForgeCaps", "progress", "streak", "lingeringRadiance")
            if set(entity) - ENTITY_COORDINATES - RETIRED_ENTITY_DATA[old] or any(entity.get(k) for k in active):
                raise ValueError(f"Retired block {old} at {position} has unhandled saved data")
            del entities[position]
        else:
            raise ValueError(f"Incompatible block entity for {old} at {position}")


def compact(states, palette, values):
    result = []
    indexes = {}
    remap = []
    for entry in palette:
        key = str(entry["Name"]), tuple(properties(entry).items())
        if key not in indexes:
            indexes[key] = len(result)
            result.append(entry)
        remap.append(indexes[key])
    write_indices(states, result, np.asarray(remap, dtype=np.intp)[values])


def update_chunk(chunk, dimension, policy, catalog, world, loot_tables, retired_fluids, report):
    entities = {tuple(int(e[k]) for k in "xyz"): e for e in chunk.get("block_entities", ())}
    if len(entities) != len(chunk.get("block_entities", ())):
        raise ValueError("Duplicate saved block entity position")
    entity_sections = Counter(y // 16 for _, y, _ in entities)
    removed_ticks = set()
    changed = False
    relight = False
    for section in chunk.get("sections", ()):
        states = section.get("block_states", {})
        palette = list(states.get("palette", ()))
        selected = [(i, str(entry["Name"])) for i, entry in enumerate(palette) if entry["Name"] in policy]
        if not selected:
            continue
        values = read_indices(states, len(palette))
        section_changed = False
        sy = int(section["Y"])
        for i, old in selected:
            occupied = np.flatnonzero(values == i)
            if not len(occupied):
                continue
            rule = policy[old]
            variant = rule.get("deep", rule) if sy < 0 else rule
            replacement = target_state(variant, palette[i], catalog)
            new = str(replacement["Name"])
            if rule.get("entity") or entity_sections[sy]:
                positions = [block_position(chunk, section, int(slot)) for slot in occupied]
                handle_entities(old, rule.get("entity"), entities, positions, world, loot_tables)
            if new in AIR and chunk.get("block_ticks"):
                removed_ticks.update((old, *block_position(chunk, section, int(slot))) for slot in occupied)
            palette[i] = replacement
            row = report.setdefault(old, {"targets": Counter(), "examples": []})
            row["targets"][new] += int(len(occupied))
            samples = row["examples"]
            if sum(s["target"] == new for s in samples) < 4 and not any(
                s["target"] == new and s["chunk"] == [int(chunk["xPos"]), int(chunk["zPos"])]
                for s in samples
            ):
                samples.append({"dimension": dimension, "position": block_position(chunk, section, int(occupied[0])),
                                "chunk": [int(chunk["xPos"]), int(chunk["zPos"])], "target": new,
                                "properties": properties(replacement), "full": chunk["Status"] == "minecraft:full"})
            section_changed = True
            relight |= rule.get("relight", False) or new in AIR
        if section_changed:
            compact(states, palette, values)
            changed = True
    if removed_ticks:
        ticks = chunk["block_ticks"]
        chunk["block_ticks"] = type(ticks)(entry for entry in ticks
            if (entry["i"], *(int(entry[k]) for k in "xyz")) not in removed_ticks)
    fluid_ticks = chunk.get("fluid_ticks", ())
    if retired_fluids and fluid_ticks:
        retained = [entry for entry in fluid_ticks if entry["i"] not in retired_fluids]
        if len(retained) != len(fluid_ticks):
            chunk["fluid_ticks"] = type(fluid_ticks)(retained)
            changed = True
    if len(entities) != len(chunk.get("block_entities", ())):
        chunk["block_entities"] = nbtlib.List[nbtlib.Compound](entities.values())
    if relight:
        chunk.pop("Heightmaps", None)
        chunk.pop("isLightOn", None)
        for section in chunk["sections"]:
            section.pop("SkyLight", None)
            section.pop("BlockLight", None)
    return changed


def apply(world, output, policy, catalog, loot_tables):
    for old, rule in policy.items():
        mode = rule.get("entity")
        for variant in (rule, rule.get("deep", rule)):
            new = variant["target"]
            if old in catalog or new not in catalog or catalog[new]["block_entity"] != (mode == "quark_lootr_chest"):
                raise ValueError(f"Invalid reviewed conversion {old} -> {new}")
            if mode in {"empty_plant", "retired_entity"} and new not in AIR:
                raise ValueError(f"Block entity removal requires an air target for {old}")
    retired_fluids = {name for rule in policy.values() for name in rule.get("fluid_ticks", ())}
    markers = tuple(name.encode() for name in policy.keys() | retired_fluids)
    stats, report = Counter(), {}
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
                    raise ValueError(f"Misplaced source chunk {coords}")
                try:
                    changed = update_chunk(chunk, dimension, policy, catalog, world, loot_tables, retired_fluids, report)
                except ValueError as error:
                    raise ValueError(f"{path.name} {coords}: {error}") from error
                if changed:
                    if original[offset + 4] & 128:
                        raise ValueError(f"Cannot rewrite an external chunk at {coords}")
                    if updated is None:
                        updated = bytearray(original)
                    replace_chunk(updated, slot, offset, updated[slot + 3], chunk)
                    stats["chunks"] += 1
            if updated is not None:
                (staging / path.relative_to(world)).write_bytes(updated)
                stats["regions"] += 1
        staging.rename(output)
    return {"view": stats, "total": sum(sum(v["targets"].values()) for v in report.values()), "blocks": report}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("loot_tables", type=Path, help="JSON array of available loot table IDs")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    world, output = args.world.resolve(), args.output.resolve()
    if not (world / "level.dat").is_file() or output.exists() or output.is_relative_to(world):
        parser.error("Pass a closed source world and a new output directory outside it")
    report = apply(world, output, json.loads(POLICY.read_text()), json.loads(args.catalog.read_text())["blocks"],
                   set(json.loads(args.loot_tables.read_text())))
    print(json.dumps(report, indent=2))
