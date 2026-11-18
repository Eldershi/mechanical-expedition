#!/usr/bin/env python3
"""Append the Alpine placement guard to the retained target-version tree definitions."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


DESIGN = Path(__file__).resolve().parents[4] / "design/tectonic-preview-20261018"
CLIMATE = DESIGN / "v2/climate"
MODIFIER = {"type": "expedition_alpine_climate:alpine_treeline"}


def selected_biomes():
    return set(json.loads((CLIMATE / "biome-policy.json").read_text())["biomes"])


def selection(biomes):
    audit = json.loads((DESIGN / "configuration/static-audit.json").read_text())
    paths = set()
    for row in audit["vegetation"]["selected"]:
        if biomes.intersection(row["biomes"]):
            namespace, name = row["feature"].split(":", 1)
            paths.add(f"data/{namespace}/worldgen/placed_feature/{name}.json")
    overrides = CLIMATE / "additional-placement-overrides"
    paths.update("data/" + f.relative_to(overrides).as_posix() for f in overrides.rglob("*.json"))
    return paths


def regions_unexplored_features(jar, names, biomes):
    paths = set()
    for biome in sorted(biomes):
        namespace, name = biome.split(":", 1)
        path = f"data/{namespace}/worldgen/biome/{name}.json"
        if namespace != "regions_unexplored" or path not in names:
            continue
        for step in json.loads(jar.read(path))["features"]:
            for feature in step:
                if feature.startswith(("regions_unexplored:tree/group/", "regions_unexplored:tree/fallen/")):
                    root = feature.split(":", 1)[1]
                    paths.add(f"data/{namespace}/worldgen/placed_feature/{root}.json")
    return paths


def build(vanilla, mods, output):
    biomes = selected_biomes()
    paths = selection(biomes)
    features = {}
    for candidate in [vanilla, *sorted(mods.glob("*.jar"))]:
        with ZipFile(candidate) as jar:
            names = set(jar.namelist())
            current = regions_unexplored_features(jar, names, biomes)
            if current:
                paths = {name for name in paths if not name.startswith("data/regions_unexplored/")} | current
            for name in paths.intersection(names):
                value = json.loads(jar.read(name))
                if name in features and features[name] != value:
                    raise ValueError(f"Conflicting target definitions of {name}")
                features[name] = value
    if not features:
        raise ValueError("No selected tree definitions were found")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as jar:
        def write(name, value):
            jar.writestr(ZipInfo(name), json.dumps(value, indent=2) + "\n", compress_type=ZIP_DEFLATED)

        write("pack.mcmeta", {"pack": {"pack_format": 48, "description": "Expedition alpine treeline"}})
        for name, feature in sorted(features.items()):
            if MODIFIER not in feature["placement"]:
                feature["placement"].append(MODIFIER)
            write(name, feature)
    print(f"Wrote {len(features)} tree placement overrides")
    for name in sorted(paths - features.keys()):
        print(f"Absent in target: {name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vanilla-data", type=Path, required=True)
    parser.add_argument("--mods", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.vanilla_data, args.mods, args.output)
