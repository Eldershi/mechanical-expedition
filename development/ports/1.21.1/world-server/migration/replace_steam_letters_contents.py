#!/usr/bin/env python3
"""Export migrated Anvil and player files for the Steam Letters removal."""

import argparse
from collections import Counter
import io
import json
from pathlib import Path

import nbtlib

from prepare_region_copy import SECTOR, read_payload, replace_chunk


NAMESPACE = "steam_letters:"
REPLACEMENTS = {
    "steam_letters:bronze_casing": "create:copper_casing",
    "steam_letters:steam": "mekanism:steam",
}


def replace_contents(node, changes):
    if isinstance(node, nbtlib.Compound):
        identifier = node.get("id")
        if isinstance(identifier, nbtlib.String) and identifier in REPLACEMENTS and ("count" in node or "amount" in node):
            target = REPLACEMENTS[str(identifier)]
            node["id"] = nbtlib.String(target)
            changes[target] += int(node.get("amount", node.get("count", 0)))
        for key, value in node.items():
            if str(key).startswith(NAMESPACE):
                raise ValueError(f"Unsupported legacy Steam Letters key {key}")
            replace_contents(value, changes)
    elif isinstance(node, nbtlib.List):
        for entry in node:
            replace_contents(entry, changes)
    elif isinstance(node, nbtlib.String) and node.startswith(NAMESPACE):
        raise ValueError(f"Unsupported legacy Steam Letters entry {node}")


def change_region(path, destination):
    data = bytearray(path.read_bytes())
    changes = Counter()
    rx, rz = map(int, path.name.split(".")[1:3])
    for slot in range(1024):
        entry = slot * 4
        offset = int.from_bytes(data[entry:entry + 3], "big") * SECTOR
        if not offset:
            continue
        coords = (rx * 32 + slot % 32, rz * 32 + slot // 32)
        payload = read_payload(data, offset, coords)
        if NAMESPACE.encode() not in payload:
            continue
        chunk = nbtlib.File.parse(io.BytesIO(payload))
        try:
            chunk_changes = Counter()
            replace_contents(chunk, chunk_changes)
        except ValueError as error:
            raise ValueError(f"{path.name} chunk {coords}: {error}") from error
        if chunk_changes:
            replace_chunk(data, entry, offset, data[entry + 3], chunk)
            changes.update(chunk_changes)
            changes["chunks"] += 1
    if changes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
    return changes


def change_player(path, destination):
    player = nbtlib.load(path)
    book = player.get("recipeBook", {})
    changes = Counter()
    for key in ("recipes", "toBeDisplayed"):
        if key in book:
            entries = book[key]
            filtered = [item for item in entries if not item.startswith(NAMESPACE)]
            if len(filtered) != len(entries):
                changes["retired_recipe_entries"] += len(entries) - len(filtered)
                book[key] = nbtlib.List[nbtlib.String](filtered)
    replace_contents(player, changes)
    if changes:
        destination.parent.mkdir(parents=True, exist_ok=True)
        player.save(destination, gzipped=True)
        changes["player_files"] += 1
    return changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    world, output = args.world.resolve(), args.output.resolve()
    if not (world / "level.dat").is_file() or output.exists() or output.is_relative_to(world):
        parser.error("Pass a saved world and a new output directory outside it")

    report = Counter()
    for path in sorted(world.rglob("r.*.mca")):
        if path.parent.name in {"region", "entities"}:
            report.update(change_region(path, output / path.relative_to(world)))
    for path in sorted((world / "playerdata").glob("*.dat")):
        report.update(change_player(path, output / path.relative_to(world)))
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
