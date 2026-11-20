#!/usr/bin/env python3
"""Restore matched Power Grid wire entities and circuit parts on a closed world copy."""

import argparse
from collections import defaultdict
from pathlib import Path

import nbtlib

from measure_chunk_edges import read_chunk
from migrate_quartz_and_peat import read_indices
from prepare_region_copy import SECTOR, replace_chunk


NETWORK = Path("data/powergrid_electric_network_data.dat")
WIRES = {"powergrid:block_wire", "powergrid:hanging_wire"}


def endpoints(first, second):
    return frozenset((tuple(map(int, node["Pos"])), int(node["Terminal"])) for node in (first, second))


def state(world, pos):
    x, y, z = pos
    chunk = read_chunk(world / "region", x // 16, z // 16)
    if chunk is None:
        return None
    for section in chunk["sections"]:
        if int(section["Y"]) == y // 16:
            data = section["block_states"]
            palette = data["palette"]
            index = (y % 16) * 256 + (z % 16) * 16 + x % 16
            return palette[int(read_indices(data, len(palette))[index])]
    return None


def rewrite(source, current, output, selected):
    version = int(nbtlib.load(current / "level.dat")["Data"]["DataVersion"])
    existing = current / NETWORK
    network = nbtlib.load(existing) if existing.is_file() else nbtlib.File(
        {"data": nbtlib.Compound({"Parts": nbtlib.List[nbtlib.Compound]()}), "DataVersion": nbtlib.Int(version)}
    )
    parts = network["data"]["Parts"]
    old_parts = nbtlib.load(source / NETWORK)["data"]["Parts"]
    by_owner = {tuple(part["Owner"]): part for part in old_parts
                if (int(part["X"]), int(part["Z"])) in selected}
    occupied = {endpoints(part["Node1"], part["Node2"]) for part in parts
                if all(part[name].get("Type") == 0 for name in ("Node1", "Node2"))}
    current_owners = {tuple(part["Owner"]) for part in parts}
    changed = defaultdict(list)
    count = 0
    for cx, cz in sorted(selected):
        old = read_chunk(source / "entities", cx, cz, full=False)
        new = read_chunk(current / "entities", cx, cz, full=False)
        if new is None:
            new = nbtlib.File({"DataVersion": nbtlib.Int(version), "Position": nbtlib.IntArray([cx, cz]),
                               "Entities": nbtlib.List[nbtlib.Compound]()})
        entities = new["Entities"]
        entity_ids = {tuple(entity["UUID"]) for entity in entities}
        existing_wires = {endpoints(entity["Endpoint1"], entity["Endpoint2"]) for entity in entities
                          if entity["id"] in WIRES
                          and all(entity[name].get("Type") == 0 for name in ("Endpoint1", "Endpoint2"))}
        modified = False
        for entity in (old or {}).get("Entities", ()):
            if entity["id"] not in WIRES:
                continue
            owner = tuple(entity["UUID"])
            part = by_owner.pop(owner, None)
            if part is None or any(part[name].get("Type") != 0 for name in ("Node1", "Node2")):
                continue
            pair = endpoints(part["Node1"], part["Node2"])
            # Multiblock wires can render at a different block from the circuit node.
            render_pair = endpoints(entity["Endpoint1"], entity["Endpoint2"])
            if pair in occupied or render_pair in existing_wires:
                continue
            if owner in current_owners or owner in entity_ids:
                raise ValueError("A saved wire UUID is already in use at different terminals")
            for pos, _ in pair | render_pair:
                block = state(source, pos)
                if block is None or not str(block["Name"]).startswith("powergrid:") or block != state(current, pos):
                    raise ValueError(f"Wire endpoint block has changed at {pos}")
            restored = nbtlib.Compound({key: value for key, value in entity.items() if key != "ForgeCaps"})
            entities.append(restored)
            parts.append(part)
            occupied.add(pair)
            existing_wires.add(render_pair)
            current_owners.add(owner)
            count += 1
            modified = True
        if modified:
            changed[f"r.{cx // 32}.{cz // 32}.mca"].append((cx, cz, new))

    if count == 0:
        return count
    write_entity_overlay(current / "entities", output / "entities", changed)
    (output / NETWORK).parent.mkdir(parents=True, exist_ok=True)
    network.save(output / NETWORK, gzipped=True)
    return count


def write_entity_overlay(current, output, changes):
    for name, chunks in changes.items():
        path = current / name
        data = bytearray(path.read_bytes()) if path.is_file() else bytearray()
        if not data:
            data.extend(bytes(2 * SECTOR))
        if len(data) < 2 * SECTOR:
            raise ValueError(f"Truncated entity region {name}")
        for cx, cz, chunk in chunks:
            index = ((cx % 32) + 32 * (cz % 32)) * 4
            offset = int.from_bytes(data[index:index + 3], "big") * SECTOR
            if offset and data[offset + 4] & 128:
                raise ValueError(f"External entity chunk at {(cx, cz)}")
            replace_chunk(data, index, offset, data[index + 3], chunk)
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument("overlay", type=Path)
    parser.add_argument("--chunk", nargs=2, type=int, action="append", required=True, metavar=("X", "Z"))
    args = parser.parse_args()
    output = args.overlay.resolve()
    if output.exists() or any(world.resolve() in output.parents for world in (args.archive, args.current)):
        parser.error("Choose a new overlay directory outside the input worlds")
    print(f"Restored wires: {rewrite(args.archive, args.current, output, set(map(tuple, args.chunk)))}")


if __name__ == "__main__":
    main()
