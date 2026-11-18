#!/usr/bin/env python3
"""Convert the Expedition radar project to the LDLib2 productive file format."""

import argparse
from pathlib import Path

from nbtlib import Byte, Compound, File, List, String, load, parse_nbt

RADAR_ID = "cmi:radar_antenna"
MACHINE_FILE = Path("multiblock/radar_antenna.mb")
RECIPE_FILE = Path("recipe_type/radar_antenna.rt")
MBD_ROOT = Path("ldlib2/assets/mbd2")
PREDICATES = Path("ldlib2/assets/ldlib2/resources/global")
FACING = ("down", "up", "north", "south", "west", "east")
UI_TEMPLATE = Path(__file__).with_name("radar-ui.snbt")


def write_tag(root, relative, tag):
    output = root / relative
    output.parent.mkdir(parents=True, exist_ok=True)
    File(tag).save(output, gzipped=False)


def convert_state(state, renderers):
    renderer = state["renderer"]["value"]
    if renderer.get("_type") == "ui_resource":
        model = renderers[renderer["key"]["key"]]
        state["renderer"]["value"] = Compound({
            "type": model["_type"],
            "data": Compound({"modelLocation": model["modelLocation"]}),
        })
    for key in ("renderer", "lightLevel", "shape", "renderingBox", "machineSound"):
        toggle = state[key]
        toggle["_enable"] = toggle.pop("enable")
    for child in state["children"]:
        convert_state(child, renderers)


def convert(source, output):
    controller = load(source / MACHINE_FILE, gzipped=False)
    recipe_type = load(source / RECIPE_FILE, gzipped=False)
    definition = controller["definition"]
    if definition["id"] != RADAR_ID or recipe_type["recipe_type"]["registryName"] != RADAR_ID:
        raise ValueError("The input is not an Expedition radar antenna project")
    if output.exists():
        raise FileExistsError(output)

    resources = controller.pop("resources")
    predicates = resources["mbd2.gui.editor.group.predicate"]
    used_predicates = {}
    for holder in controller["placeholders"]["holders"]:
        holder["facing"] = String(FACING[int(holder["facing"])])
        for index, legacy in enumerate(holder["predicates"]):
            if legacy["type"] != "builtin":
                raise ValueError(f"Unrecognized radar predicate source {legacy}")
            key = str(legacy["key"])
            path = PREDICATES / f"radar_{key.replace(':', '_')}.predicate.nbt"
            if key in {"any", "air"}:
                # Use the world-loaded predicate resource on dedicated servers.
                used_predicates[path] = Compound({"type": String(key)})
            else:
                predicate = predicates[key]
                if predicate["_type"] != "blocks":
                    raise ValueError(f"Unrecognized radar predicate {key}")
                used_predicates[path] = Compound({
                    "type": String("blocks"),
                    "blocks": List[String](entry["p"] for entry in predicate["blocks"]),
                })
            holder["predicates"][index] = Compound({"built-in": Byte(0), "path": String(path.as_posix())})

    settings = definition["recipeLogicSettings"]
    settings["_enable"] = settings.pop("enable")
    if settings.pop("recipeModifiers"):
        raise ValueError("The radar project uses unsupported legacy recipe modifiers")
    convert_state(definition["stateMachine"]["root"], resources["ldlib.gui.editor.group.renderer"])
    machine = definition["machineSettings"]
    machine["uiTemplate"] = parse_nbt(UI_TEMPLATE.read_text(encoding="utf-8"))
    for trait in machine["traitDefinitions"]:
        trait["type"] = trait.pop("_type")
        trait["slotNames"] = List[String](entry["p"] for entry in trait["slotNames"] if entry["p"])

    controller.pop("ui", None)
    recipe_type.pop("ui", None)
    recipe_type.pop("fuelUI", None)
    recipe_type.pop("resources", None)
    for path, predicate in used_predicates.items():
        write_tag(output, path, {"type": String("predicate"), "data": predicate})
    write_tag(output, MBD_ROOT / MACHINE_FILE, {"data": Compound(controller)})
    write_tag(output, MBD_ROOT / RECIPE_FILE, {"data": Compound(recipe_type)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="the old ldlib/assets/mbd2 directory")
    parser.add_argument("output", type=Path, help="new directory for the generated installation tree")
    args = parser.parse_args()
    convert(args.source, args.output)
