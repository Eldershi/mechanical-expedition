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
PARTS = {
    ".": ("any", None),
    "A": ("air", None),
    "R": ("blocks", NAMESPACE + ":riveted_frame"),
    "P": ("blocks", NAMESPACE + ":structural_panel"),
    "W": ("blocks", NAMESPACE + ":insulated_window"),
}


def write(output, relative, tag):
    path = output / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    File(tag).save(path, gzipped=False)


def build(output):
    sys.path.insert(0, str(RADAR))
    from convert_project import convert

    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as temp:
        converted = Path(temp) / "radar"
        convert(ROOT / "pack/ldlib/assets/mbd2", converted)
        radar = load(converted / MACHINES / "radar_antenna.mb", gzipped=False)["data"]

    markers = [*PARTS, "C"]
    holders = []
    for index, marker in enumerate(markers):
        predicates = []
        if marker != "C":
            kind, block = PARTS[marker]
            predicate = Compound({"type": String(kind)})
            if block is not None:
                predicate["blocks"] = List[String]([String(block)])
            relative = GLOBAL / f"expedition_space_{index}.predicate.nbt"
            write(output, relative, {"type": String("predicate"), "data": predicate})
            predicates.append(Compound({"built-in": Byte(0), "path": String(relative.as_posix())}))
        holders.append(Compound({"facing": String("north"), "isController": Byte(marker == "C"),
                                 "predicates": List[Compound](predicates)}))

    fixtures = {}
    for name, layers in json.loads((HERE / "structures.json").read_text()).items():
        x_size, y_size, z_size = len(layers[0][0]), len(layers), len(layers[0])
        if any(len(layer) != z_size or any(len(row) != x_size for row in layer) for layer in layers):
            raise ValueError(f"Invalid pattern dimensions: {name}")
        pattern = [layers[y][z][x] for x in range(x_size) for y in range(y_size) for z in range(z_size)]
        if pattern.count("C") != 1:
            raise ValueError(f"Expected one controller: {name}")
        project = copy.deepcopy(radar)
        definition = project["definition"]
        definition["id"] = String(f"{NAMESPACE}:{name}")
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
        root = definition["stateMachine"]["root"]
        root["children"] = List[Compound]()
        root["renderer"]["value"]["data"]["modelLocation"] = String(f"{NAMESPACE}:block/{name}")
        root["shape"]["_enable"] = Byte(0)
        root["renderingBox"]["_enable"] = Byte(0)
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
                    if marker not in ".A":
                        cells.append([x, y, z, f"{NAMESPACE}:{name}" if marker == "C" else PARTS[marker][1]])
        fixtures[name] = cells
    return fixtures


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--fixtures", type=Path)
    options = parser.parse_args()
    fixtures = build(options.output)
    if options.fixtures:
        options.fixtures.write_text(json.dumps(fixtures, indent=2) + "\n")
