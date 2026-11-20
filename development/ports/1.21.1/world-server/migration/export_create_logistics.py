#!/usr/bin/env python3
"""Export legacy Create chain links and frogport bindings for a live-world repair."""

import argparse
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import zlib

import nbtlib


CHAIN = "create:chain_conveyor"
FROGPORTS = {"create:package_frogport", "fluidlogistics:copper_frogport"}
IDS = {CHAIN, *FROGPORTS}
NEEDLES = tuple(value.encode() for value in IDS)
DECOMPRESS = {1: gzip.decompress, 2: zlib.decompress, 3: bytes}


def position(value):
    if isinstance(value, nbtlib.Compound):
        return tuple(int(value[axis]) for axis in "XYZ")
    if len(value) != 3:
        raise ValueError(f"Invalid block position: {value}")
    return tuple(map(int, value))


def add(a, b):
    return tuple(x + y for x, y in zip(a, b, strict=True))


def dimensions(world):
    yield "minecraft:overworld", world / "region"
    yield "minecraft:the_nether", world / "DIM-1/region"
    yield "minecraft:the_end", world / "DIM1/region"
    custom = world / "dimensions"
    for path in sorted(custom.rglob("region")):
        namespace, *parts = path.relative_to(custom).parts[:-1]
        yield namespace + ":" + "/".join(parts), path


def entities(regions):
    for path in sorted(regions.glob("r.*.*.mca")):
        data = path.read_bytes()
        rx, rz = map(int, path.name.split(".")[1:3])
        for slot in range(1024):
            header = slot * 4
            offset = int.from_bytes(data[header:header + 3], "big") * 4096
            if not offset:
                continue
            end = offset + 4 + int.from_bytes(data[offset:offset + 4], "big")
            compression = data[offset + 4]
            if compression & 128:
                cx, cz = rx * 32 + slot % 32, rz * 32 + slot // 32
                payload = (regions / f"c.{cx}.{cz}.mcc").read_bytes()
            else:
                payload = data[offset + 5:end]
            raw = DECOMPRESS[compression & 127](payload)
            if not any(needle in raw for needle in NEEDLES):
                continue
            chunk = nbtlib.File.parse(io.BytesIO(raw))
            for entity in chunk.get("block_entities", ()):
                identifier = str(entity.get("id", ""))
                if identifier in IDS:
                    yield tuple(int(entity[key]) for key in "xyz"), identifier, entity


def topology(world):
    result = {}
    for dimension, directory in dimensions(world):
        chains, ports = {}, {}
        for pos, identifier, entity in entities(directory):
            if identifier == CHAIN:
                chains[pos] = {add(pos, position(target)) for target in entity.get("Connections", ())}
            else:
                ports[pos] = (identifier, entity.get("Target"))
        if chains or ports:
            result[dimension] = (chains, ports)
    return result


def manifest(topology):
    result = {"schema": 1, "links": [], "ports": []}
    skipped = Counter()
    for dimension, (chains, ports) in sorted(topology.items()):
        for a, neighbors in sorted(chains.items()):
            for b in sorted(neighbors):
                if a == b or a not in chains.get(b, ()):
                    skipped["unconfirmed_chain_links"] += 1
                elif a < b:
                    result["links"].append({"dimension": dimension, "first": a, "second": b})
        for source, (identifier, target) in sorted(ports.items()):
            if not target:
                skipped["ports_without_binding"] += 1
                continue
            kind = str(target.get("Type", ""))
            if kind not in {"ChainConveyor", "TrainStation", "create:chain_conveyor", "create:train_station"}:
                skipped["unrecognized_port_target"] += 1
                continue
            chain = kind in {"ChainConveyor", "create:chain_conveyor"}
            row = {"dimension": dimension, "position": source, "blockEntity": identifier,
                   "relativePos": position(target["RelativePos"]),
                   "type": "chain_conveyor" if chain else "train_station"}
            if chain:
                row["chainPos"] = float(target["ChainPos"])
                row["flipped"] = bool(target.get("Flipped", False))
                if "Connection" in target:
                    row["connection"] = position(target["Connection"])
            result["ports"].append(row)
    return result, skipped


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if not (args.world / "level.dat").is_file():
        parser.error("The source must be a Minecraft world")
    data, skipped = manifest(topology(args.world))
    with args.output.open("x") as stream:
        json.dump(data, stream, indent=2)
        stream.write("\n")
    print(f"{len(data['links'])} reciprocal chain links; {len(data['ports'])} bound frogports")
    if skipped:
        print(dict(skipped))


if __name__ == "__main__":
    main()
