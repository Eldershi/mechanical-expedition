#!/usr/bin/env python3
"""Recover a legacy Create mining bearing's missing assembled contraption."""

import argparse
from collections import Counter
from pathlib import Path
import json
import math

import nbtlib

from measure_chunk_edges import read_chunk
from restore_powergrid_wiring import state, write_entity_overlay


def block_pos(value):
    if isinstance(value, nbtlib.Compound):
        return nbtlib.IntArray([value[axis] for axis in "XYZ"])
    return value


def controller(entity):
    relative = block_pos(entity["ControllerRelative"])
    return tuple(math.floor(point) + offset for point, offset in zip(entity["Pos"], relative, strict=True))


def convert_stack(stack, registered, aliases, totals):
    source = str(stack["id"])
    target = aliases.get(source, source)
    if target not in registered or not set(stack) <= {"id", "Count", "Slot"}:
        raise ValueError(f"Unsupported mining contraption item {source}")
    count = int(stack["Count"])
    if not 1 <= count <= 64:
        raise ValueError(f"Unexpected mining contraption stack count for {source}")
    stack["id"] = nbtlib.String(target)
    stack["count"] = nbtlib.Int(count)
    del stack["Count"]
    totals[target] += count


def migrate(entity, registered, aliases):
    entity.pop("ForgeCaps", None)
    entity["ControllerRelative"] = block_pos(entity["ControllerRelative"])
    scene = entity["Contraption"]
    scene["Anchor"] = block_pos(scene["Anchor"])
    for actor in scene.get("Actors", ()):
        actor["Pos"] = block_pos(actor["Pos"])
    for group in scene.get("CapturedMultiblocks", ()):
        group["Controller"] = block_pos(group["Controller"])
        group["Parts"] = nbtlib.List[nbtlib.Compound](
            nbtlib.Compound({"Pos": block_pos(part)}) for part in group["Parts"]
        )
    for block in scene["Blocks"]["BlockList"]:
        for key in ("Data", "UpdateTag"):
            payload = block.get(key, {})
            payload.pop("ForgeCaps", None)
            for location in ("Controller", "LastKnownPos"):
                if location in payload:
                    payload[location] = block_pos(payload[location])
            for stack in payload.get("Inventory", {}).get("Items", ()):
                convert_stack(stack, registered, aliases, Counter())
    totals = Counter()
    for entry in scene.get("items", ()):
        entry["pos"] = block_pos(entry["pos"])
        for stack in entry["storage"]["value"]["items"].values():
            convert_stack(stack, registered, aliases, totals)
    return totals


def repair(archive, current, output, pos, registry, aliases):
    x, y, z = pos
    cx, cz = x // 16, z // 16
    original = read_chunk(archive / "entities", cx, cz, full=False)
    if original is None:
        raise ValueError("Missing source contraption chunk")
    saved, = [entity for entity in original["Entities"]
              if entity["id"] == "create:stationary_contraption" and controller(entity) == pos]
    previous = state(archive, pos)
    if previous is None or previous["Name"] != "create_rns:miner_bearing" or previous != state(current, pos):
        raise ValueError("Mining bearing no longer matches the archive")
    block_chunk = read_chunk(current / "region", cx, cz)
    bearing, = [tag for tag in block_chunk["block_entities"]
                if tuple(tag[key] for key in "xyz") == pos and tag["id"] == "create_rns:miner_bearing"]
    if not bearing.get("Running"):
        raise ValueError("The current mining bearing is not marked as assembled")
    version = block_chunk["DataVersion"]
    current_entity_dir = current / "entities"
    destination = read_chunk(current_entity_dir, cx, cz, full=False)
    if destination is None:
        destination = nbtlib.File({"DataVersion": version, "Position": nbtlib.IntArray([cx, cz]),
                                   "Entities": nbtlib.List[nbtlib.Compound]()})
    for entity in destination["Entities"]:
        if tuple(entity["UUID"]) == tuple(saved["UUID"]) or (
            entity["id"] == saved["id"] and controller(entity) == pos
        ):
            raise ValueError("The current world already has a contraption for this bearing")
    totals = migrate(saved, set(registry), aliases)
    destination["Entities"].append(saved)
    filename = f"r.{cx // 32}.{cz // 32}.mca"
    write_entity_overlay(current_entity_dir, output, {filename: [(cx, cz, destination)]})
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("overlay", type=Path)
    parser.add_argument("--bearing", nargs=3, type=int, required=True, metavar=("X", "Y", "Z"))
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--aliases", type=Path, required=True)
    args = parser.parse_args()
    if args.overlay.exists() or any(
        world.resolve() in args.overlay.resolve().parents for world in (args.archive, args.current)
    ):
        parser.error("Choose a new overlay directory outside both worlds")
    registry = json.loads(args.registry.read_text())["items"]
    aliases = json.loads(args.aliases.read_text())
    print(json.dumps(repair(args.archive, args.current, args.overlay, tuple(args.bearing), registry, aliases)))


if __name__ == "__main__":
    main()
