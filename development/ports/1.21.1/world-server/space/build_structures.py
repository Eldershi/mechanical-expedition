#!/usr/bin/env python3
"""Build the five Multiblocked2 structures and their fixture coordinates."""

import argparse
import copy
import json
from pathlib import Path
import sys

from nbtlib import Byte, Compound, File, Int, IntArray, List, String, load

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
RADAR = HERE.parent.parent / "radar-mbd2"
NAMESPACE = "expedition_space"
GLOBAL = Path("ldlib2/assets/ldlib2/resources/global")
MACHINES = Path("ldlib2/assets/mbd2/multiblock")
CONTROLLER = "m"
ANY = " "


def property_pairs(value):
    block, sep, props = value.partition("[")
    return block, dict(pair.split("=", 1) for pair in props[:-1].split(",")) if sep else {}


def predicate_for(value, alternatives):
    if value is None:
        return Compound({"type": String("any")})
    if value in alternatives:
        return Compound({"type": String("blocks"), "blocks": List[String](map(String, alternatives[value]))})
    if value.startswith("#"):
        raise ValueError(f"Unmapped pattern tag: {value}")
    block, props = property_pairs(value)
    if props:
        return Compound({"type": String("partial_state"), "block": String(block),
                         "requirements": List[Compound]([Compound({"property": String(k), "value": String(v)})
                                                        for k, v in props.items()])})
    return Compound({"type": String("blocks"), "blocks": List[String]([String(block)])})


def write(output, relative, tag):
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    File(tag).save(path, gzipped=False)


def radar_template():
    sys.path.insert(0, str(RADAR))
    from convert_project import convert

    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as temp:
        converted = Path(temp) / "radar"
        convert(ROOT / "pack/ldlib/assets/mbd2", converted)
        return load(converted / MACHINES / "radar_antenna.mb", gzipped=False)["data"]


def build_layouts(output, namespace, layouts, configure, alternatives):
    radar = radar_template()
    fixtures = {}
    for name, definition_data in layouts.items():
        layers = definition_data["layout"]
        part_names = definition_data["blocks"]
        fixture_states = definition_data.get("fixture_states", {})
        markers = [ANY, CONTROLLER, *part_names]
        optional = set(definition_data.get("optional", []))
        ui_access = definition_data.get("ui_access")
        wildcard = GLOBAL / f"{namespace}_{name}_0.predicate.nbt"
        holders = []
        for index, marker in enumerate(markers):
            predicates = []
            if marker != CONTROLLER:
                predicate = predicate_for(part_names.get(marker), alternatives)
                if ui_access is not None:
                    predicate["allowOpenUI"] = Byte(marker in ui_access)
                relative = GLOBAL / f"{namespace}_{name}_{index}.predicate.nbt"
                write(output, relative, {"type": String("predicate"), "data": predicate})
                predicates.append(Compound({"built-in": Byte(0), "path": String(relative.as_posix())}))
                if marker in optional:
                    predicates.append(Compound({"built-in": Byte(0), "path": String(wildcard.as_posix())}))
            holders.append(Compound({"facing": String("north"), "isController": Byte(marker == CONTROLLER),
                                     "predicates": List[Compound](predicates)}))

        x_size, y_size, z_size = len(layers[0][0]), len(layers), len(layers[0])
        if any(len(layer) != z_size or any(len(row) != x_size for row in layer) for layer in layers):
            raise ValueError(f"Invalid pattern dimensions: {name}")
        pattern = [layers[y][z][x] for x in range(x_size) for y in range(y_size) for z in range(z_size)]
        if pattern.count(CONTROLLER) != 1:
            raise ValueError(f"Expected one controller: {name}")
        project = copy.deepcopy(radar)
        definition = project["definition"]
        definition["id"] = String(f"{namespace}:{name}")
        root = definition["stateMachine"]["root"]
        root["children"] = List[Compound]()
        root["renderer"]["value"]["data"]["modelLocation"] = String(f"{namespace}:block/{name}")
        root["shape"]["_enable"] = Byte(0)
        root["renderingBox"]["_enable"] = Byte(0)
        configure(name, definition)
        project["placeholders"] = Compound({
            "x": Int(x_size), "y": Int(y_size), "z": Int(z_size),
            "pattern": IntArray([markers.index(marker) for marker in pattern]),
            "holders": List[Compound](holders),
        })
        project["aisle_repetitions"] = IntArray([1] * (4 * y_size))
        write(output, MACHINES / f"{name}.mb", {"data": project})

        cells = []
        for y, layer in enumerate(layers):
            for z, row in enumerate(layer):
                for x, marker in enumerate(row):
                    if marker == ANY:
                        continue
                    selected = f"{namespace}:{name}" if marker == CONTROLLER else part_names[marker]
                    if selected in alternatives:
                        selected = alternatives[selected][0]
                    cells.append([x, y, z, fixture_states.get(f"{x},{y},{z}", selected)])
        fixtures[name] = cells
    return fixtures


def configure_space(name, definition):
    definition["recipeLogicSettings"]["_enable"] = Byte(0)
    machine = definition["machineSettings"]
    energy = next(t for t in machine["traitDefinitions"] if t["name"] == "forge_energy_storage")
    energy["capacity"] = Int(256_000)
    energy["maxReceive"] = Int(4_000)
    energy["maxExtract"] = Int(256_000)
    machine["traitDefinitions"] = List[Compound]([energy])
    machine["hasUI"] = Byte(0)
    machine.pop("uiTemplate", None)
    definition["itemProperties"]["creativeTab"]["enable"] = Byte(0)


def build(output):
    layouts = json.loads((HERE / "structures.json").read_text())
    alternatives = {"#dut_create:metal_girder": ["create:metal_girder", "create:metal_girder_encased_shaft"]}
    return build_layouts(output, NAMESPACE, layouts, configure_space, alternatives)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fixtures", type=Path)
    options = parser.parse_args()
    fixtures = build(options.output)
    if options.fixtures:
        options.fixtures.write_text(json.dumps(fixtures, indent=2) + "\n")
