#!/usr/bin/env python3
"""Supply Tinkers' placed features and retain existing Expedition recipe IDs."""

import argparse
import json
from pathlib import Path
from zipfile import ZipFile


FEATURES = (
    "cobalt_ore_large", "cobalt_ore_small", "earth_geode", "ender_geode",
    "ichor_geode", "sky_geode",
)
CASTING_RECIPES = (
    "smeltery/casting/metal/brass/block",
    "smeltery/casting/metal/copper/block",
)
FUEL = {
    "biodiesel": ("createdieselgenerators:biodiesel", 1636),
    "blazing_blood": ("{namespace}:blazing_blood", 2638),
}


def build(legacy, target, pack, namespace):
    def write(path, value):
        output = pack / path
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(value)

    with ZipFile(legacy) as old, ZipFile(target) as new:
        for kind in ("configured_feature", "placed_feature"):
            for name in FEATURES:
                path = f"data/tconstruct/worldgen/{kind}/{name}.json"
                if namespace == "tconstruct" and path not in new.namelist():
                    write(path, old.read(path).replace(b'"forge:', b'"c:').replace(b'"#forge:', b'"#c:'))
        for path in CASTING_RECIPES:
            alias = f"selected_native/tconstruct/{path}"
            recipe = json.loads(new.read(f"data/{namespace}/recipe/{path}.json"))
            if "id" in recipe:
                recipe["id"] = f"expedition:{alias}"
            write(f"data/expedition/recipe/{alias}.json", (json.dumps(recipe, indent=2) + "\n").encode())
    for name, (fluid, temperature) in FUEL.items():
        path = f"tconstruct/fuel/{name}"
        recipe = {
            "type": f"{namespace}:melting_fuel",
            "id": f"expedition:{path}",
            "duration": 150,
            "fluid": {"amount": 50, "fluid": fluid.format(namespace=namespace)},
            "rate": temperature // 100,
            "temperature": temperature,
        }
        write(f"data/expedition/recipe/{path}.json", (json.dumps(recipe, indent=2) + "\n").encode())
    metadata = {"pack": {"pack_format": 48, "description": "Expedition Tinkers' Construct data"}}
    write("pack.mcmeta", (json.dumps(metadata, indent=2) + "\n").encode())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("legacy", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("pack", type=Path)
    parser.add_argument("--namespace", choices=("tconstruct", "modernfoundry"), required=True)
    args = parser.parse_args()
    build(args.legacy, args.target, args.pack, args.namespace)
