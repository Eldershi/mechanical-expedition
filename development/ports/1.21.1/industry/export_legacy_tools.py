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
MATERIALS = {"feather", "gunpowder", "knightmetal", "prismarine", "string", "wood"}
UPGRADES = {"redirected"}
LEGACY = "tconstruct:"
MODERN = "modernfoundry:"


def renamed(resource):
    return String(MODERN + resource.removeprefix(LEGACY)) if resource.startswith(LEGACY) else resource


def remap_tinkers_data(data):
    if isinstance(data, Compound):
        return Compound({renamed(key): remap_tinkers_data(value) for key, value in data.items()})
    if isinstance(data, List):
        return type(data)(remap_tinkers_data(value) for value in data)
    return renamed(data) if isinstance(data, String) else data


def convert_stack(source):
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
    missing_materials = set(data.get("tic_materials", [])) - {LEGACY + material for material in MATERIALS}
    if missing_materials:
        raise ValueError("Missing Hexa materials: " + ", ".join(sorted(missing_materials)))
    missing_upgrades = {entry.get("name", "") for entry in data.get("tic_upgrades", [])} - {
        LEGACY + modifier for modifier in UPGRADES
    }
    if missing_upgrades:
        raise ValueError("Missing Hexa upgrades: " + ", ".join(sorted(missing_upgrades)))
    if data.get("tic_persistent"):
        raise ValueError("Persistent tool data needs an explicit mapping")

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
    if "Damage" in data:
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


def region_report(region):
    for chunk in chunks(region):
        if "xPos" in chunk and "zPos" in chunk:
            coordinates = [int(chunk["xPos"]), int(chunk["zPos"])]
        else:
            coordinates = [int(axis) for axis in chunk["Position"]]
        for location, stack in stacks(chunk):
            row = {"chunk": coordinates, "path": location, "source": stack.snbt()}
            try:
                row["target"] = convert_stack(stack).snbt()
            except ValueError as error:
                row["withheld"] = str(error)
            yield row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("regions", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = {f"{region.parent.name}/{region.name}": list(region_report(region)) for region in args.regions}
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, ensure_ascii=False, indent=2)
        output.write("\n")


if __name__ == "__main__":
    main()
