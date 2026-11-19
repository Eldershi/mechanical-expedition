#!/usr/bin/env python3
"""Stage supported parts, tools, and materials from Create vault recovery."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from nbtlib import Compound, Int, List, String, load

from export_legacy_tools import LEGACY, TOOLS, convert_stack
from legacy_create_workpieces import WORKPIECES, convert_create_workpiece

WORLD_SERVER = Path(__file__).resolve().parent.parent / "world-server"
sys.path.insert(0, str(WORLD_SERVER / "migration"))
sys.path.insert(0, str(WORLD_SERVER / "player-inventory-migration"))
from measure_chunk_edges import read_chunk
from prepare_region_copy import SECTOR, replace_chunk
from spell_components import SPELL_CONTAINER, convert_scroll


VAULT = "create:item_vault"
SCROLL = "irons_spellbooks:scroll"
TARGET_VERSION = 3955
EQUIVALENT_STACKS = {"cmi:simple_battery": "createaddition:capacitor"}
EQUIVALENT_STACKS.update({f"tconstruct:{name}": f"modernfoundry:{name}" for name in (
    "gear_cast",
    "liquid_soul_bucket",
    "molten_brass_bucket",
    "molten_bronze_bucket",
    "molten_copper_bucket",
    "necrotic_bone",
    "part_builder",
    "scorched_brick",
    "seared_basin",
    "seared_brick",
    "seared_bricks",
    "seared_bricks_slab",
    "seared_bricks_wall",
    "seared_chute",
    "seared_drain",
    "seared_duct",
    "seared_fancy_bricks",
    "seared_faucet",
    "seared_fuel_tank",
    "seared_glass",
    "seared_table",
    "seared_triangle_bricks",
    "sky_slime_ball",
    "sky_slime_sapling",
    "smeltery_controller",
)})


def candidates(recovery, report, include_legacy_pan_materials, include_equivalent_stacks,
               include_create_workpieces, target_spells):
    locations = set()
    for index, entry in enumerate(recovery.get("Stacks", ())):
        original = entry.get("OriginalStack", {})
        item = str(original.get("id", ""))
        tool = item.startswith(LEGACY) and item.removeprefix(LEGACY) in TOOLS
        equivalent_item = EQUIVALENT_STACKS.get(item) if include_equivalent_stacks else None
        workpiece = include_create_workpieces and item in WORKPIECES
        scroll = target_spells is not None and item == SCROLL
        if (entry.get("BlockEntity") != VAULT
                or entry.get("Reason") not in {"missing_item_id", "unverified_mod_payload"}
                or not (tool or equivalent_item or workpiece or scroll)
                or "Slot" not in original):
            continue
        position = tuple(map(int, entry["BlockPos"]))
        slot = int(original["Slot"])
        details = {"position": position, "slot": slot, "source_item": item}
        if (position, slot) in locations:
            raise ValueError(f"Duplicate tool recovery entry at {position}, slot {slot}")
        locations.add((position, slot))
        try:
            if scroll:
                stack = convert_scroll(original)
                payload = stack["components"][SPELL_CONTAINER]
                if len(payload["data"]) != 1 or payload["maxSpells"] != 1:
                    raise ValueError("Expected one spell in the scroll")
                spell = str(payload["data"][0]["id"])
                if spell not in target_spells:
                    raise ValueError(f"Spell is missing from the target registry: {spell}")
            elif workpiece:
                stack = convert_create_workpiece(original)
            elif equivalent_item:
                count = int(original.get("Count", 0))
                if set(original) != {"id", "Count", "Slot"} or not 1 <= count <= 64:
                    raise ValueError("Expected a stack with only its original item, count, and slot")
                stack = Compound({"id": String(equivalent_item), "count": Int(count)})
            else:
                stack = convert_stack(original, include_legacy_pan_materials)
                if int(stack["count"]) != 1:
                    raise ValueError("Expected one tool")
        except ValueError as error:
            report["withheld"].append(dict(details, reason=str(error)))
            continue
        stack["Slot"] = Int(slot)
        yield index, details, stack


def normalized_stack(stack):
    fields = dict(stack)
    components = fields.get("components", {})
    if components.get("minecraft:damage") == 0:
        # Minecraft omits the default damage component when saving a zero-wear tool.
        fields["components"] = {key: value for key, value in components.items() if key != "minecraft:damage"}
        if not fields["components"]:
            del fields["components"]
    return fields


def restore_chunk(chunk, entries, report, completed):
    vaults = {tuple(int(entity[axis]) for axis in "xyz"): entity
              for entity in chunk.get("block_entities", ()) if entity.get("id") == VAULT}
    changed = False
    for index, details, stack in entries:
        position, slot = details["position"], details["slot"]
        inventory = vaults.get(position, {}).get("Inventory", {})
        items = inventory.get("Items")
        if not isinstance(items, List) or not 0 <= slot < int(inventory.get("Size", 0)):
            report["withheld"].append(dict(details, reason="Target vault or slot does not match"))
            continue
        if not items and items.subtype is not Compound:
            # Empty NBT lists can be serialized as TAG_End instead of TAG_Compound.
            items = inventory["Items"] = List[Compound]()
        occupying = [item for item in items if int(item.get("Slot", -1)) == slot]
        if occupying:
            if len(occupying) == 1 and normalized_stack(occupying[0]) == normalized_stack(stack):
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


def stage_tools(target, recovery, output, include_legacy_pan_materials=False,
                include_equivalent_stacks=False, include_create_workpieces=False, target_spells=None):
    report = {"restored": [], "already_valid": [], "withheld": [], "regions": []}
    regions = defaultdict(lambda: defaultdict(list))
    for entry in candidates(recovery, report, include_legacy_pan_materials,
                            include_equivalent_stacks, include_create_workpieces, target_spells):
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
    parser.add_argument("--include-legacy-pan-materials", action="store_true",
                        help="Recover matching old pans with the industry KubeJS materials")
    parser.add_argument("--include-equivalent-stacks", action="store_true",
                        help="Recover CMI capacitors and matching Modern Foundry stock without item payloads")
    parser.add_argument("--include-create-workpieces", action="store_true",
                        help="Recover verified Create assembly stages, belt selections, and unworn tools")
    parser.add_argument("--spell-registry", type=Path,
                        help="Restore scrolls for IDs in a target server spell registry export")
    args = parser.parse_args()
    target, output = args.target_regions.resolve(), args.output.resolve()
    if not target.is_dir() or output.exists() or target in output.parents:
        parser.error("Use a migrated region directory and a new output directory outside it")
    target_spells = None
    if args.spell_registry:
        registry = json.loads(args.spell_registry.read_text())
        keys = registry.get("spells") if isinstance(registry, dict) else None
        if (not isinstance(keys, list) or not all(isinstance(key, str) for key in keys)
                or "irons_spellbooks:magic_missile" not in keys):
            parser.error("Expected a target spell registry JSON export with a spells array")
        target_spells = frozenset(keys)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="foundry-tools-", dir=output.parent) as temp:
        stage = Path(temp) / "regions"
        stage.mkdir()
        report = stage_tools(target, load(args.vault_recovery), stage,
                             args.include_legacy_pan_materials,
                             args.include_equivalent_stacks, args.include_create_workpieces, target_spells)
        (stage / "foundry-tool-report.json").write_text(json.dumps(report, indent=2) + "\n")
        if output.exists():
            raise FileExistsError(output)
        stage.rename(output)
    print(json.dumps({key: len(value) for key, value in report.items()}, sort_keys=True))


if __name__ == "__main__":
    main()
