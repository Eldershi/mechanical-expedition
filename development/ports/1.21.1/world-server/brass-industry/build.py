#!/usr/bin/env python3
"""Generate the NeoForge industrial structure and recipe-type definitions."""

import argparse
import copy
import json
from pathlib import Path
import sys

from nbtlib import Byte, Compound, Int, List, String

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "space"))
from build_structures import MACHINES, build_layouts, write

NAMESPACE = "expedition_industry"
FLUID_INPUT = {"alloy_furnace", "electro_hydro_resonant_tower", "electrolytic_cell",
               "huge_crusher", "hydropress", "infinity_fetching_pool", "large_difference_engine", "shaft_furnace"}
FLUID_OUTPUT = {"alloy_furnace", "condenser", "electro_hydro_resonant_tower", "electrolytic_cell",
                "infinity_fetching_pool", "shaft_furnace"}


def node(kind, data, index):
    return Compound({"type": String(kind), "index": Int(index), "data": Compound(data)})


def row(template, item_counts, kind):
    indexed = [f"ui:{name}_{i}" for name, count in item_counts for i in range(count)]
    children = List[Compound]([node(kind, {"id": String(name)}, i) for i, name in enumerate(indexed)])
    return node("element", {"children": children, "classes": List[String]([String("radar-slots")])},
                len(template["children"]))


def configure(machine_name, definition):
    settings = definition["recipeLogicSettings"]
    settings["recipeType"] = String(f"{NAMESPACE}:{machine_name}")
    settings["consumeInputsAfterWorking"] = Byte(1)
    machine = definition["machineSettings"]
    originals = {str(t["name"]): t for t in machine["traitDefinitions"]}
    rows = [("item_input", 4), ("item_output", 4)]
    for name, count in rows:
        originals[name]["slotSize"] = Int(count)
        originals[name]["slotLimit"] = Int(64)
    energy = originals["forge_energy_storage"]
    energy["capacity"] = Int(256_000)
    energy["maxReceive"] = Int(8_000)
    traits = [originals[name] for name, _ in rows] + [energy]
    fluids = []
    for suffix, io, names in (("input", "IN", FLUID_INPUT), ("output", "OUT", FLUID_OUTPUT)):
        if machine_name in names:
            name = f"fluid_{suffix}"
            fluids.append((name, 2))
            traits.append(Compound({
                "type": String("fluid_tank"), "name": String(name), "tankSize": Int(2),
                "capacity": Int(16_000), "allowSameFluids": Byte(0),
                "guiIO": String("BOTH" if suffix == "input" else "OUT"),
                "recipeHandlerIO": String(io),
                "capabilityIO": Compound({face: String(io) for face in energy["capabilityIO"]}),
            }))
    machine["traitDefinitions"] = List[Compound](traits)
    machine["hasUI"] = Byte(1)
    template = machine["uiTemplate"]["template"]
    children = template["children"]
    del children[1]
    children.insert(1, row(template, rows, "item-slot"))
    if fluids:
        children.insert(2, row(template, fluids, "fluid-slot"))
    for i, child in enumerate(children):
        child["index"] = Int(i)
    children[0]["data"]["text"]["translate"] = String(f"block.{NAMESPACE}.{machine_name}")
    definition["itemProperties"]["creativeTab"]["enable"] = Byte(0)


def build(output):
    layouts = json.loads((HERE / "structures.json").read_text())
    alternatives = json.loads((HERE / "structure-alternatives.json").read_text())
    for name in layouts:
        definition = Compound({
            "registryName": String(f"{NAMESPACE}:{name}"), "requireFuelForWorking": Byte(0),
            "isXEIVisible": Byte(1), "isProxyRecipeXEIVisible": Byte(0),
            "builtinRecipes": Compound(), "icon": Compound({
                "type": String("item"), "items": List[Compound]([
                    Compound({"id": String(f"{NAMESPACE}:{name}"), "count": Int(1)})
                ])
            }),
        })
        write(output, MACHINES.parent / "recipe_type" / f"expedition_{name}.rt",
              {"data": Compound({"recipe_type": definition})})
    return build_layouts(output, NAMESPACE, layouts, configure, alternatives)


if __name__ == "__main__":
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("output", type=Path)
    args.add_argument("--fixtures", type=Path)
    options = args.parse_args()
    result = build(options.output)
    if options.fixtures:
        options.fixtures.write_text(json.dumps(result, indent=2) + "\n")
