#!/usr/bin/env python3
"""Copy a prepared world and migrate retired Expedition blocks and items."""

import argparse
from collections import Counter
import gzip
import io
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

import nbtlib
import numpy as np

from prepare_region_copy import SECTOR, read_payload, replace_chunk


BLOCKS = {
    "cmi:quartz_ore": "minecraft:nether_quartz_ore",
    "cmi:deepslate_quartz_ore": "minecraft:nether_quartz_ore",
    "cmi:peat_block": "minecraft:mud",
    "cmi:iron_deposit_block": "create_rns:iron_deposit_block",
    "cmi:platinum_ore_node": "cmi:platinum_deposit_block",
    "cmi:cheese_ore_node": "cmi:cheese_deposit_block",
}
COLLECTIBLES = {
    "cmi:parchment": ("minecraft:paper", "奇怪的羊皮纸"),
    "cmi:torn_parchment_a": ("minecraft:paper", "撕开的羊皮纸（甲）"),
    "cmi:torn_parchment_b": ("minecraft:paper", "撕开的羊皮纸（乙）"),
    "cmi:frost_cake_base": ("minecraft:pumpkin_pie", "寒霜蛋糕胚"),
    "fluidlogistics:frost_cake": ("minecraft:pumpkin_pie", "寒霜蛋糕"),
}
ITEMS = {
    **BLOCKS,
    **{name: item for name, (item, _) in COLLECTIBLES.items()},
    "cmi:peat_block": "immersiveengineering:coal_coke",
    "cmi:peat": "minecraft:charcoal",
    "cmi:enriched_silicon": "cmi:single_crystal_silicon",
}
ADVANCEMENTS = {"cmi:echoes_north_star", "cmi:echoes_south_cross", "cmi:meet"}
RECIPES = {"cmi:minecraft/shaped/love_manual_only"} | {
    f"{prefix}{suffix}"
    for prefix in ("fluidlogistics:cooling/frost_cake", "thermal:compat/fluidlogistics/bottler_create_frost_cake")
    for suffix in ("", "2", "3")
}
RETIRED = {*ITEMS, "cmi:obsidian_cell"}
MARKERS = tuple(name.encode() for name in RETIRED | RECIPES)
ME_CELL = "ae2:storage_cell_inv"
ITEM_KEY = "ae2:i"
SECTION_VOLUME = 4096


def has_retired_content(payload):
    return any(marker in payload for marker in MARKERS)


def read_indices(states, palette_size):
    if palette_size == 1:
        return np.zeros(SECTION_VOLUME, dtype=np.intp)
    bits = max(4, (palette_size - 1).bit_length())
    per_long = 64 // bits
    packed = np.asarray(states["data"], dtype=np.int64).view(np.uint64)
    if len(packed) != (SECTION_VOLUME + per_long - 1) // per_long:
        raise ValueError("Invalid Anvil block palette data length")
    offsets = np.arange(0, per_long * bits, bits, dtype=np.uint64)
    values = ((packed[:, None] >> offsets) & ((1 << bits) - 1)).ravel()[:SECTION_VOLUME]
    if values.max() >= palette_size:
        raise ValueError("Anvil block palette index exceeds its palette")
    return values.astype(np.intp)


def replace_palette(states, report):
    palette = states.get("palette", ())
    targets = [(i, str(state["Name"])) for i, state in enumerate(palette) if state["Name"] in BLOCKS]
    if not targets:
        return
    values = read_indices(states, len(palette))
    counts = np.bincount(values, minlength=len(palette))
    for i, name in targets:
        state = palette[i]
        if state.get("Properties"):
            raise ValueError(f"Unexpected properties on retired state {name}")
        state["Name"] = nbtlib.String(BLOCKS[name])
        report[f"blocks/{name}"] += int(counts[i])

    compact = []
    remap = []
    positions = {}
    for state in palette:
        key = str(state["Name"]), tuple(sorted(state.get("Properties", {}).items()))
        if key not in positions:
            positions[key] = len(compact)
            compact.append(state)
        remap.append(positions[key])
    if len(compact) == len(palette):
        return
    write_indices(states, compact, np.asarray(remap, dtype=np.uint64)[values])


def write_indices(states, palette, indices):
    states["palette"] = nbtlib.List[nbtlib.Compound](palette)
    if len(palette) == 1:
        states.pop("data", None)
        return
    bits = max(4, (len(palette) - 1).bit_length())
    per_long = 64 // bits
    indices = np.pad(np.asarray(indices, dtype=np.uint64), (0, (-SECTION_VOLUME) % per_long))
    offsets = np.arange(0, per_long * bits, bits, dtype=np.uint64)
    packed = np.bitwise_or.reduce(indices.reshape(-1, per_long) << offsets, axis=1)
    states["data"] = nbtlib.LongArray(packed.view(np.int64))


def replace_item(entry, name, legacy):
    entry["id"] = nbtlib.String(ITEMS[name])
    if name not in COLLECTIBLES:
        return
    title = nbtlib.String(json.dumps({"text": COLLECTIBLES[name][1]}, ensure_ascii=False))
    if legacy:
        display = entry.setdefault("tag", nbtlib.Compound()).setdefault("display", nbtlib.Compound())
        custom_name, lore = "Name", "Lore"
    else:
        display = entry.setdefault("components", nbtlib.Compound())
        custom_name, lore = "minecraft:custom_name", "minecraft:lore"
    if custom_name not in display:
        display[custom_name] = title
    elif display[custom_name] != title:
        display.setdefault(lore, nbtlib.List[nbtlib.String]()).append(title)


def merge_cell_entries(entries, amounts, report, legacy=False):
    if len(entries) != len(amounts):
        raise ValueError("ME cell amounts do not match its keys")
    changed_keys = set()
    for entry, amount in zip(entries, amounts, strict=True):
        name = entry.get("id")
        if entry.get("#t") == ITEM_KEY and name in ITEMS:
            if amount <= 0:
                raise ValueError("Invalid retired item amount in ME cell")
            report[f"me_items/{name}"] += amount
            replace_item(entry, name, legacy)
            changed_keys.add(entry["id"])
    if not changed_keys:
        return None

    merged, totals = [], []
    positions = {}
    for entry, amount in zip(entries, amounts, strict=True):
        if entry.get("#t") == ITEM_KEY and entry.get("id") in changed_keys:
            components = entry.get("components", entry.get("tag", nbtlib.Compound()))
            key = entry["id"], nbtlib.serialize_tag(sorted_compounds(components), compact=True)
            index = positions.get(key)
            if index is not None:
                totals[index] += amount
                report["merged_me_keys"] += 1
                continue
            positions[key] = len(merged)
        merged.append(entry)
        totals.append(amount)
    if any(not 0 < amount < 2**63 for amount in totals):
        raise ValueError("ME cell amount cannot be stored as a positive long")
    return merged, totals


def sorted_compounds(value):
    if isinstance(value, nbtlib.Compound):
        return nbtlib.Compound({key: sorted_compounds(value[key]) for key in sorted(value)})
    if isinstance(value, nbtlib.List):
        return type(value)(sorted_compounds(entry) for entry in value)
    return value


def replace_contents(node, report):
    if isinstance(node, nbtlib.List):
        for entry in node:
            replace_contents(entry, report)
    elif isinstance(node, nbtlib.Compound):
        name = node.get("id")
        amount = node.get("realCount", node.get("count", node.get("Count")))
        if isinstance(name, nbtlib.String) and name in ITEMS and isinstance(amount, (nbtlib.Byte, nbtlib.Int, nbtlib.Long)):
            report[f"stack_items/{name}"] += int(amount)
            replace_item(node, name, legacy="Count" in node and "components" not in node)
        elif node.get("#t") == ITEM_KEY and isinstance(name, nbtlib.String) and name in ITEMS:
            report[f"me_references/{name}"] += 1
            replace_item(node, name, legacy="tag" in node and "components" not in node)
        state = node.get("Name")
        if isinstance(state, nbtlib.String) and state in BLOCKS:
            if node.get("Properties"):
                raise ValueError(f"Unexpected properties on retired state {state}")
            report[f"other_states/{state}"] += 1
            node["Name"] = nbtlib.String(BLOCKS[state])
        deposit = node.get("deposit_block")
        if isinstance(deposit, nbtlib.String) and deposit in BLOCKS and "deposit" in BLOCKS[deposit]:
            report[f"deposit_processes/{deposit}"] += 1
            node["deposit_block"] = nbtlib.String(BLOCKS[deposit])

        if ME_CELL in node:
            entries = node[ME_CELL]
            if any(entry.get("id") in ITEMS for entry in entries):
                result = merge_cell_entries(entries, [int(entry["#"]) for entry in entries], report)
                if result is not None:
                    merged, amounts = result
                    for entry, count in zip(merged, amounts, strict=True):
                        entry["#"] = nbtlib.Long(count)
                    node[ME_CELL] = type(entries)(merged)
        if isinstance(node.get("keys"), nbtlib.List) and isinstance(node.get("amts"), nbtlib.LongArray):
            entries = node["keys"]
            if any(entry.get("id") in ITEMS for entry in entries):
                result = merge_cell_entries(entries, list(map(int, node["amts"])), report, legacy=True)
                if result is not None:
                    merged, amounts = result
                    node["keys"] = type(entries)(merged)
                    node["amts"] = nbtlib.LongArray(amounts)
        for key in ("recipeBook", "recipe_book"):
            if isinstance(book := node.get(key), nbtlib.Compound):
                for list_key in ("recipes", "toBeDisplayed", "known", "highlight"):
                    if isinstance(values := book.get(list_key), nbtlib.List[nbtlib.String]):
                        retained = type(values)(entry for entry in values if entry not in RECIPES)
                        if len(retained) != len(values):
                            report["removed_collectible_recipes"] += len(values) - len(retained)
                            book[list_key] = retained
        for value in node.values():
            replace_contents(value, report)
    elif isinstance(node, nbtlib.String) and node in RETIRED:
        raise ValueError(f"Unsupported retired-content reference {node}")


def change_region(path):
    data = bytearray(path.read_bytes())
    report = Counter()
    if not data:
        return report
    if len(data) < 2 * SECTOR:
        raise ValueError("Short Anvil region header")
    rx, rz = map(int, path.name.split(".")[1:3])
    for slot in range(1024):
        entry = slot * 4
        offset = int.from_bytes(data[entry:entry + 3], "big") * SECTOR
        if not offset:
            continue
        coords = (rx * 32 + slot % 32, rz * 32 + slot // 32)
        payload = read_payload(data, offset, coords, path)
        if not has_retired_content(payload):
            continue
        chunk = nbtlib.File.parse(io.BytesIO(payload))
        changes = Counter()
        try:
            for section in chunk.get("sections", ()):
                replace_palette(section.get("block_states", {}), changes)
            replace_contents(chunk, changes)
        except ValueError as error:
            raise ValueError(f"Chunk {coords}: {error}") from error
        if changes:
            external = data[offset + 4] & 128
            replace_chunk(data, entry, offset, data[entry + 3], chunk)
            if external:
                x, z = coords
                (path.parent / f"c.{x}.{z}.mcc").unlink()
            report.update(changes)
            report["changed_chunks"] += 1
    if report:
        path.write_bytes(data)
    return report


def replace_nbt(path):
    payload = path.read_bytes()
    gzipped = payload.startswith(b"\x1f\x8b")
    payload = gzip.decompress(payload) if gzipped else payload
    if not has_retired_content(payload):
        return Counter()
    data = nbtlib.File.parse(io.BytesIO(payload))
    report = Counter()
    replace_contents(data, report)
    if report:
        data.save(path, gzipped=gzipped)
    return report


def remove_collectible_advancements(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    found = data.keys() & ADVANCEMENTS
    for key in found:
        del data[key]
    if found:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(found)


def migrate(source, output):
    if output.exists() or output.is_relative_to(source):
        raise ValueError("Output must be a new directory outside the source world")
    level = nbtlib.load(source / "level.dat")
    if level["Data"]["DataVersion"] != 3955:
        raise ValueError("Prepare a Minecraft 1.21.1 level.dat before migrating retired materials")
    if any(path.is_symlink() for path in source.rglob("*")):
        raise ValueError("Source world contains symbolic links")
    with TemporaryDirectory(dir=output.parent) as directory:
        target = Path(directory) / "world"
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("session.lock", "level.dat_old"))
        report = Counter()
        for path in sorted(target.rglob("*")):
            try:
                if path.suffix == ".mca" and path.parent.name in {"region", "entities"}:
                    report.update(change_region(path))
                elif path.is_file() and path.suffix in {".dat", ".nbt", ".dat_old"}:
                    counts = replace_nbt(path)
                    report.update({f"backups/{key}": count for key, count in counts.items()}
                                  if path.suffix == ".dat_old" else counts)
                elif path.suffix == ".json" and path.parent.name == "advancements":
                    removed = remove_collectible_advancements(path)
                    if removed:
                        report["removed_collectible_advancements"] += removed
            except (ValueError, OSError) as error:
                raise ValueError(f"{path.relative_to(target)}: {error}") from error
        target.rename(output)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    options = parser.parse_args()
    report = migrate(options.source.resolve(), options.output.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
