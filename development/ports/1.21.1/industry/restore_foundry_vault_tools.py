#!/usr/bin/env python3
"""Stage supported Hexa tools and Nebula materials from Create vault recovery."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from nbtlib import Compound, Int, List, String, load

from export_legacy_tools import LEGACY, TOOLS, convert_stack

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "world-server" / "migration"))
from measure_chunk_edges import read_chunk
from prepare_region_copy import SECTOR, replace_chunk


VAULT = "create:item_vault"
TARGET_VERSION = 3955
NEBULA_MATERIALS = {"nebula_tinker:spider_fang"}


def candidates(recovery, report, include_nebula):
    locations = set()
    for index, entry in enumerate(recovery.get("Stacks", ())):
        original = entry.get("OriginalStack", {})
        item = str(original.get("id", ""))
        tool = item.startswith(LEGACY) and item.removeprefix(LEGACY) in TOOLS
        nebula_material = include_nebula and item in NEBULA_MATERIALS
        if (entry.get("BlockEntity") != VAULT
                or entry.get("Reason") not in {"missing_item_id", "unverified_mod_payload"}
                or not (tool or nebula_material)
                or "Slot" not in original):
            continue
        position = tuple(map(int, entry["BlockPos"]))
        slot = int(original["Slot"])
        details = {"position": position, "slot": slot, "source_item": item}
        if (position, slot) in locations:
            raise ValueError(f"Duplicate tool recovery entry at {position}, slot {slot}")
        locations.add((position, slot))
        try:
            if nebula_material:
                count = int(original.get("Count", 0))
                if set(original) != {"id", "Count", "Slot"} or not 1 <= count <= 64:
                    raise ValueError("Expected an unmodified Nebula material stack")
                stack = Compound({"id": String(item), "count": Int(count)})
            else:
                stack = convert_stack(original)
                if int(stack["count"]) != 1:
                    raise ValueError("Expected one tool")
        except ValueError as error:
            report["withheld"].append(dict(details, reason=str(error)))
            continue
        stack["Slot"] = Int(slot)
        yield index, details, stack


def restore_chunk(chunk, entries, report, completed):
    vaults = {tuple(int(entity[axis]) for axis in "xyz"): entity
              for entity in chunk.get("block_entities", ()) if entity.get("id") == VAULT}
    changed = False
    for index, details, stack in entries:
        position, slot = details["position"], details["slot"]
        inventory = vaults.get(position, {}).get("Inventory", {})
        items = inventory.get("Items")
        if items is None or not 0 <= slot < int(inventory.get("Size", 0)):
            report["withheld"].append(dict(details, reason="Target vault or slot does not match"))
            continue
        occupying = [item for item in items if int(item.get("Slot", -1)) == slot]
        if occupying:
            if occupying == [stack]:
                report["already_valid"].append(details)
                completed.add(index)
            else:
                report["withheld"].append(dict(details, reason="Target slot is occupied"))
            continue
        items.append(stack)
        report["restored"].append(dict(details, target_item=str(stack["id"])))
        completed.add(index)
        changed = True
    return changed


def stage_tools(target, recovery, output, include_nebula=False):
    report = {"restored": [], "already_valid": [], "withheld": [], "regions": []}
    regions = defaultdict(lambda: defaultdict(list))
    for entry in candidates(recovery, report, include_nebula):
        x, _, z = entry[1]["position"]
        regions[(x // 512, z // 512)][(x // 16, z // 16)].append(entry)

    completed = set()
    for (rx, rz), chunks in sorted(regions.items()):
        name = f"r.{rx}.{rz}.mca"
        region = None
        for (cx, cz), entries in sorted(chunks.items()):
            chunk = read_chunk(target, cx, cz)
            if chunk is None or int(chunk.get("DataVersion", 0)) != TARGET_VERSION:
                for _, details, _ in entries:
                    report["withheld"].append(dict(details, reason="Expected a migrated 1.21.1 chunk"))
                continue
            if not restore_chunk(chunk, entries, report, completed):
                continue
            if region is None:
                region = bytearray((target / name).read_bytes())
            pointer = ((cz % 32) * 32 + cx % 32) * 4
            offset = int.from_bytes(region[pointer:pointer + 3], "big") * SECTOR
            if region[offset + 4] & 128:
                raise ValueError(f"External region storage is unsupported for {(cx, cz)}")
            replace_chunk(region, pointer, offset, region[pointer + 3], chunk)
        if region is not None:
            (output / name).write_bytes(region)
            report["regions"].append(name)

    recovery["Stacks"] = List[Compound](entry for index, entry in enumerate(recovery.get("Stacks", ()))
                                        if index not in completed)
    recovery.save(output / "unconverted-stacks.nbt", gzipped=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-regions", required=True, type=Path, help="Region directory of a stopped migration copy")
    parser.add_argument("--vault-recovery", required=True, type=Path, help="Remaining Create vault recovery NBT")
    parser.add_argument("--output", required=True, type=Path, help="New directory for changed region files and recovery")
    parser.add_argument("--include-nebula", action="store_true",
                        help="Recover supported materials when the Nebula Tinker adapter is installed")
    args = parser.parse_args()
    target, output = args.target_regions.resolve(), args.output.resolve()
    if not target.is_dir() or output.exists() or target in output.parents:
        parser.error("Use a migrated region directory and a new output directory outside it")
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="foundry-tools-", dir=output.parent) as temp:
        stage = Path(temp) / "regions"
        stage.mkdir()
        report = stage_tools(target, load(args.vault_recovery), stage, args.include_nebula)
        (stage / "foundry-tool-report.json").write_text(json.dumps(report, indent=2) + "\n")
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    print(json.dumps({key: len(value) for key, value in report.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
