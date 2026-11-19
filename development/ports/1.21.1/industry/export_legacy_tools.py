#!/usr/bin/env python3
"""Export supported old Tinkers item stacks with their source NBT paths."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
import sys

from nbtlib import Compound, Int, List, String

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tconstruct"))
from export_smelteries import chunks


TOOLS = {"arrow", "fishing_rod", "melting_pan", "shuriken", "swasher"}
PARTS_AND_BOOKS = {
    "arrow_head", "encyclopedia", "fantastic_foundry", "materials_and_you",
    "mighty_smelting", "puny_smelting", "tinkers_gadgetry",
}
MATERIALS = {
    "cobalt", "feather", "gunpowder", "knightmetal", "lead", "prismarine",
    "rose_gold", "steel", "steeleaf", "string", "wood",
}
UPGRADES = {"redirected"}
TANK_FLUIDS = {"minecraft:lava", "minecraft:water", "tconstruct:powdered_snow"}
LEGACY = "tconstruct:"
MODERN = "modernfoundry:"
PAN_MATERIALS = {
    ("tconstruct:lead", "thermalconstruct:lumium"): "expedition:legacy_lumium",
    ("cmi:cast_iron", "thermalconstruct:soul_infused"): "expedition:legacy_soul_infused",
}


def renamed(resource):
    return String(MODERN + resource.removeprefix(LEGACY)) if resource.startswith(LEGACY) else resource


def remap_tinkers_data(data):
    if isinstance(data, Compound):
        return Compound({renamed(key): remap_tinkers_data(value) for key, value in data.items()})
    if isinstance(data, List):
        return type(data)(remap_tinkers_data(value) for value in data)
    return renamed(data) if isinstance(data, String) else data


def convert_persistent_data(data):
    persistent = data.get("tic_persistent")
    if not persistent:
        return
    key = "tconstruct:tank_fluid"
    if not isinstance(persistent, Compound) or persistent.keys() != {key}:
        raise ValueError("Persistent tool data needs an explicit mapping")
    fluid = persistent[key]
    if not isinstance(fluid, Compound) or fluid.keys() != {"FluidName", "Amount"}:
        raise ValueError("Unsupported saved tool tank format")
    resource = fluid["FluidName"]
    if resource not in TANK_FLUIDS:
        raise ValueError(f"Unsupported saved tool tank fluid {resource}")
    amount = int(fluid["Amount"])
    capacity = data.get("tic_stats", {}).get("tconstruct:tank_capacity", 0)
    if not 0 < amount <= capacity:
        raise ValueError(f"Saved tool tank amount {amount} is outside capacity {capacity}")
    persistent[key] = Compound({"id": renamed(resource), "amount": Int(amount)})


def convert_stack(source, include_legacy_pan_materials=False):
    old_id = str(source["id"])
    if not old_id.startswith(LEGACY):
        raise ValueError(f"Unsupported source item {old_id}")
    path = old_id.removeprefix(LEGACY)
    if path not in TOOLS | PARTS_AND_BOOKS:
        raise ValueError(f"No verified Hexa item mapping for {old_id}")
    if source.get("ForgeCaps") or source.keys() - {"id", "Count", "Slot", "tag", "ForgeCaps"}:
        raise ValueError("Unsupported legacy stack properties")

    data = deepcopy(source.get("tag", Compound()))
    if (path in TOOLS) != bool(data.get("tic_materials")):
        raise ValueError("Unexpected tool material data")
    for field in ("tic_modifiers", "tic_upgrades"):
        if field in data:
            entries = data[field]
            if not isinstance(entries, List) or any(not isinstance(entry, Compound) for entry in entries):
                raise ValueError(f"Unsupported legacy tool data in {field}")
            data[field] = type(entries)(entry for entry in entries
                                        if not entry.get("name", "").startswith("nebula_tinker:"))
    materials = data.get("tic_materials", [])
    missing_materials = set(materials) - {LEGACY + material for material in MATERIALS}
    pan_material = PAN_MATERIALS.get(tuple(materials)) if include_legacy_pan_materials and path == "melting_pan" else None
    if pan_material:
        materials[1] = String(pan_material)
        missing_materials.clear()
        for modifier in data.get("tic_modifiers", []):
            if modifier.get("name") == "thermalconstruct:luminescence":
                modifier["name"] = String("expedition:legacy_luminescence")
    if missing_materials:
        raise ValueError("Missing Hexa materials: " + ", ".join(sorted(missing_materials)))
    missing_upgrades = {entry.get("name", "") for entry in data.get("tic_upgrades", [])} - {
        LEGACY + modifier for modifier in UPGRADES
    }
    if missing_upgrades:
        raise ValueError("Missing Hexa upgrades: " + ", ".join(sorted(missing_upgrades)))
    convert_persistent_data(data)

    components = Compound()
    display = data.pop("display", Compound())
    if display.keys() - {"Name", "Lore"}:
        raise ValueError("Unsupported legacy display properties")
    if "Name" in display:
        name = json.loads(display["Name"])
        if isinstance(name, dict) and str(name.get("translate", "")).startswith("item.tconstruct."):
            name["translate"] = name["translate"].replace("item.tconstruct.", "item.modernfoundry.", 1)
        components["minecraft:custom_name"] = String(json.dumps(name, ensure_ascii=False))
    if "Lore" in display:
        components["minecraft:lore"] = display["Lore"]
    if data.get("Damage", 0):
        components["minecraft:damage"] = Int(data["Damage"])
    if data:
        components["minecraft:custom_data"] = remap_tinkers_data(data)
    result = Compound({"id": String(MODERN + path), "count": Int(source["Count"])})
    if "Slot" in source:
        result["Slot"] = source["Slot"]
    if components:
        result["components"] = components
    return result


def stacks(tag, location=()):
    if isinstance(tag, Compound):
        resource = tag.get("id")
        if isinstance(resource, String) and resource.startswith(LEGACY) and "Count" in tag:
            yield location, tag
        for key, value in tag.items():
            yield from stacks(value, (*location, key))
    elif isinstance(tag, List):
        for index, value in enumerate(tag):
            yield from stacks(value, (*location, index))


def region_report(region, include_legacy_pan_materials=False):
    for chunk in chunks(region):
        if "xPos" in chunk and "zPos" in chunk:
            coordinates = [int(chunk["xPos"]), int(chunk["zPos"])]
        else:
            coordinates = [int(axis) for axis in chunk["Position"]]
        for location, stack in stacks(chunk):
            row = {"chunk": coordinates, "path": location, "source": stack.snbt()}
            try:
                row["target"] = convert_stack(stack, include_legacy_pan_materials).snbt()
            except ValueError as error:
                row["withheld"] = str(error)
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("regions", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--include-legacy-pan-materials", action="store_true",
                        help="Convert matching pan materials for the industry KubeJS overlay")
    args = parser.parse_args()
    report = {f"{region.parent.name}/{region.name}": list(region_report(region, args.include_legacy_pan_materials))
              for region in args.regions}
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
