#!/usr/bin/env python3
"""Select entity and point-of-interest chunks for an island terrain graft."""

import argparse
from contextlib import ExitStack
import json
from pathlib import Path
import re
import shutil
import tempfile


SECTOR = 4096
ENTRIES = 1024
REGION_FILE = re.compile(r"r\.(-?\d+)\.(-?\d+)\.mca")


def read_plan(file):
    plan = json.loads(file.read_text())
    chunks = {}
    for name in ("core", "transition"):
        for point in plan[name]:
            if len(point) != 2 or any(type(value) is not int for value in point):
                raise ValueError(f"Invalid chunk coordinate {point}")
            if tuple(point) in chunks:
                raise ValueError(f"Duplicate chunk coordinate {point}")
            chunks[tuple(point)] = name
    return chunks


def region_names(directory):
    return {p.name for p in directory.glob("r.*.mca") if REGION_FILE.fullmatch(p.name)}


def merge_region(name, old, fresh, output, chunks):
    region_x, region_z = map(int, REGION_FILE.fullmatch(name).groups())
    old_path, new_path = old / name, fresh / name
    positions = bytearray(SECTOR)
    timestamps = bytearray(SECTOR)
    with ExitStack() as files:
        readers = []
        for path in (old_path, new_path):
            reader = files.enter_context(path.open("rb")) if path.is_file() and path.stat().st_size else None
            header = reader.read(SECTOR * 2) if reader else None
            if reader and len(header) != SECTOR * 2:
                raise ValueError(f"Invalid region header {path}")
            readers.append((reader, header, path.parent))
        writer = None
        for i in range(ENTRIES):
            chunk_x = 32 * region_x + i % 32
            chunk_z = 32 * region_z + i // 32
            section = chunks.get((chunk_x, chunk_z))
            if section == "transition":
                continue
            reader, header, directory = readers[0 if section == "core" else 1]
            if reader is None:
                continue
            entry = 4 * i
            source_sector = int.from_bytes(header[entry : entry + 3], "big")
            if source_sector == 0:
                continue
            source_size = header[entry + 3]
            if source_sector < 2 or source_size == 0:
                raise ValueError(f"Invalid location for chunk {(chunk_x, chunk_z)}")
            reader.seek(SECTOR * source_sector)
            raw = reader.read(SECTOR * source_size)
            length = int.from_bytes(raw[:4], "big")
            if len(raw) != SECTOR * source_size or not 1 <= length <= len(raw) - 4:
                raise ValueError(f"Truncated chunk {(chunk_x, chunk_z)}")
            if raw[4] & 128:
                external = f"c.{chunk_x}.{chunk_z}.mcc"
                shutil.copyfile(directory / external, output / external)
            if writer is None:
                writer = files.enter_context((output / name).open("xb"))
                writer.seek(SECTOR * 2)
            positions[entry : entry + 3] = (writer.tell() // SECTOR).to_bytes(3, "big")
            positions[entry + 3] = source_size
            timestamps[entry : entry + 4] = header[SECTOR + entry : SECTOR + entry + 4]
            writer.write(raw)
        if writer is not None:
            writer.seek(0)
            writer.write(positions)
            writer.write(timestamps)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old-world", required=True, type=Path)
    parser.add_argument("--fresh-world", required=True, type=Path)
    parser.add_argument("--chunk-plan", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output = args.output.resolve()
    inputs = (args.old_world.resolve(), args.fresh_world.resolve())
    if inputs[0] == inputs[1] or any(not world.is_dir() for world in inputs):
        parser.error("Supply two distinct saved world directories")
    if args.output.exists() or any(world in args.output.parents for world in inputs):
        parser.error("Use a new output directory outside the input worlds")
    chunks = read_plan(args.chunk_plan)
    with tempfile.TemporaryDirectory(prefix=".island-aux-", dir=args.output.parent) as directory:
        staging = Path(directory) / "aux"
        for name in ("entities", "poi"):
            old, fresh, output = (world / name for world in (args.old_world, args.fresh_world, staging))
            output.mkdir(parents=True)
            for region in sorted(region_names(old) | region_names(fresh)):
                merge_region(region, old, fresh, output, chunks)
        if args.output.exists():
            raise FileExistsError(args.output)
        staging.rename(args.output)


if __name__ == "__main__":
    main()
