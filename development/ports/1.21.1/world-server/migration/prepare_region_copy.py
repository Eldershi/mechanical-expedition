#!/usr/bin/env python3
"""Transfer retained block IDs on a copy or clear specified proto chunks for seam tests."""

import argparse
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import tempfile
import zlib

import nbtlib

from prepare_create_railway import convert_curve


SECTOR = 4096
OLD_SPAWNER = "tongdarailway_for_forge:track_spawner"
NEW_SPAWNER = nbtlib.String("tongdarailway:track_spawner")
CREATE_TRACK = "create:track"
EIDOLON_ORES = {
    f"eidolon:{ore}": nbtlib.String(f"eidolon_repraised:{ore}")
    for ore in ("silver_ore", "lead_ore", "deep_silver_ore", "deep_lead_ore")
}


def converted_blocks(chunk, tracks, ores, create_curves):
    for section in chunk.get("sections", ()):
        for state in section.get("block_states", {}).get("palette", ()):
            name = str(state["Name"])
            if tracks and name == OLD_SPAWNER:
                state["Name"] = NEW_SPAWNER
                yield "spawner_palette_entries"
            elif ores and name in EIDOLON_ORES:
                state["Name"] = EIDOLON_ORES[name]
                yield f"palette_entries/{name}"
    if tracks or create_curves:
        for entity in chunk.get("block_entities", ()):
            kind = entity.get("id")
            if tracks and kind == OLD_SPAWNER:
                entity["id"] = NEW_SPAWNER
                yield "spawner_block_entities"
            elif create_curves and kind == CREATE_TRACK:
                for connection in entity.get("Connections", ()):
                    if convert_curve(connection):
                        yield "create_bezier_connections"


def read_payload(data, offset, coords, region=None):
    length = int.from_bytes(data[offset : offset + 4], "big")
    compression = data[offset + 4]
    payload = data[offset + 5 : offset + 4 + length]
    if compression & 128 and region is not None:
        x, z = coords
        payload = (region.parent / f"c.{x}.{z}.mcc").read_bytes()
        compression &= 127
    if compression == 2:
        return zlib.decompress(payload)
    if compression == 1:
        return gzip.decompress(payload)
    if compression == 3:
        return payload
    raise ValueError(f"Unsupported compression {compression} in selected chunk {coords}")


def replace_chunk(data, position, offset, previous_sectors, chunk):
    uncompressed = io.BytesIO()
    chunk.write(uncompressed)
    payload = zlib.compress(uncompressed.getvalue())
    entry = (len(payload) + 1).to_bytes(4, "big") + bytes([2]) + payload
    sectors = (len(entry) + SECTOR - 1) // SECTOR
    if sectors > 255:
        raise ValueError("Rewritten chunk exceeds the inline Anvil sector limit")
    if sectors > previous_sectors:
        offset = (len(data) + SECTOR - 1) // SECTOR * SECTOR
        data.extend(bytes(offset - len(data)))
        data.extend(bytes(sectors * SECTOR))
    data[offset : offset + sectors * SECTOR] = entry.ljust(sectors * SECTOR, b"\x00")
    data[position : position + 4] = (offset // SECTOR).to_bytes(3, "big") + bytes([sectors])


def rewrite(path, target, fresh, tracks, ores, create_curves):
    regions = path.name.split(".")[1:3]
    base_x, base_z = (int(coord) * 32 for coord in regions)
    data = bytearray(path.read_bytes())
    counts = Counter()
    prefixes = []
    if tracks:
        prefixes.append(OLD_SPAWNER.encode())
    if ores:
        prefixes.extend(name.encode() for name in EIDOLON_ORES)
    if create_curves:
        prefixes.append(CREATE_TRACK.encode())
    if len(data) < 2 * SECTOR:
        return counts
    for i in range(1024):
        position = i * 4
        offset = int.from_bytes(data[position : position + 3], "big") * SECTOR
        if offset == 0:
            continue
        previous_sectors = data[position + 3]
        coords = (base_x + i % 32, base_z + i // 32)
        if not prefixes and coords not in fresh:
            continue
        payload = read_payload(data, offset, coords)
        if coords not in fresh and not any(prefix in payload for prefix in prefixes):
            continue
        chunk = nbtlib.File.parse(io.BytesIO(payload))
        if coords in fresh and chunk["Status"] not in {"full", "minecraft:full"}:
            data[position : position + 4] = bytes(4)
            data[SECTOR + position : SECTOR + position + 4] = bytes(4)
            counts["proto_chunks_cleared"] += 1
            continue
        changes = list(converted_blocks(chunk, tracks, ores, create_curves))
        if changes:
            replace_chunk(data, position, offset, previous_sectors, chunk)
            counts.update(changes)
    if counts:
        with tempfile.NamedTemporaryFile(dir=target, delete=False) as file:
            file.write(data)
        Path(file.name).replace(target / path.name)
    return counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-regions", required=True, type=Path)
    parser.add_argument("--target-regions", required=True, type=Path)
    parser.add_argument("--track-spawners", action="store_true")
    parser.add_argument("--eidolon-ores", action="store_true")
    parser.add_argument("--create-curves", action="store_true")
    parser.add_argument("--fresh-neighbor", action="append", nargs=2, type=int, metavar=("X", "Z"), default=[])
    options = parser.parse_args()
    if options.source_regions.resolve() == options.target_regions.resolve():
        parser.error("Source and target must be different copies")
    selected = {tuple(point) for point in options.fresh_neighbor}
    report = Counter()
    for source in sorted(options.source_regions.glob("r.*.mca")):
        report.update(rewrite(source, options.target_regions, selected, options.track_spawners,
                              options.eidolon_ores, options.create_curves))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
