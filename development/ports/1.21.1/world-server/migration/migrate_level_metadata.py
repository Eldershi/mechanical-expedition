#!/usr/bin/env python3
"""Build a Java 1.21.1 level.dat candidate while retaining the saved terrain settings."""

import argparse
import gzip
from pathlib import Path

import nbtlib


OVERWORLD = "minecraft:overworld"
TWILIGHT = "twilightforest:twilight_forest"
REMOVED_BIOME = "terramity:scorched_caves"
OPTIONAL_DIMENSIONS = {
    "edenring:edenring",
    "cmi:dionysus",
    "cmi:dionysus_orbit",
    "cmi:hephaestus",
    "cmi:hephaestus_orbit",
}


def migrate_overworld(generator):
    for node in compounds(generator):
        if (node.get("type") == "minecraft:uniform" and isinstance(node.get("value"), nbtlib.Compound)
                and set(node["value"]) == {"min_inclusive", "max_inclusive"}):
            node.update(node.pop("value"))

    generator["biome_source"]["biomes"] = without(
        generator["biome_source"]["biomes"], lambda item: item["biome"] == REMOVED_BIOME
    )
    for node in compounds(generator["settings"]["surface_rule"]):
        if node.get("type") == "minecraft:sequence":
            node["sequence"] = without(
                node["sequence"],
                lambda rule: list(rule.get("if_true", {}).get("biome_is", ())) == [REMOVED_BIOME],
            )


def without(current, drop):
    return type(current)(item for item in current if not drop(item))


def compounds(value):
    if isinstance(value, nbtlib.Compound):
        yield value
        for child in value.values():
            yield from compounds(child)
    elif isinstance(value, nbtlib.List):
        for child in value:
            yield from compounds(child)


def migrate(original, target, source_world):
    data = original["Data"]
    settings = data["WorldGenSettings"]
    dimensions = settings["dimensions"]
    target_data = target["Data"]
    target_dimensions = target_data["WorldGenSettings"]["dimensions"]
    unavailable = dimensions.keys() - target_dimensions.keys()
    if unexpected := unavailable - OPTIONAL_DIMENSIONS:
        raise ValueError(f"Unclassified dimension definitions: {', '.join(sorted(unexpected))}")

    for name in sorted(unavailable):
        namespace, path = name.split(":", 1)
        world = source_world / "dimensions" / namespace / path
        if any(world.rglob("*.mca")):
            raise ValueError(f"Missing target dimension with region files: {name}")

    migrate_overworld(dimensions[OVERWORLD]["generator"])
    if TWILIGHT in dimensions:
        dimensions[TWILIGHT] = target_dimensions[TWILIGHT]
    for name in unavailable:
        del dimensions[name]
    for name in target_dimensions.keys() - dimensions.keys():
        dimensions[name] = target_dimensions[name]
    data["DataPacks"] = target_data["DataPacks"]
    return unavailable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-level", required=True, type=Path)
    parser.add_argument("--fresh-target-level", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    options = parser.parse_args()
    original = nbtlib.load(options.source_level)
    target = nbtlib.load(options.fresh_target_level)
    try:
        omitted = migrate(original, target, options.source_level.parent)
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    with options.output.open("xb") as raw, gzip.GzipFile(fileobj=raw, filename="", mode="wb") as output:
        original.write(output)
    print(f"Wrote {options.output}")
    for name in sorted(omitted):
        print(f"Omitted unavailable dimension definition with no region files: {name}")


if __name__ == "__main__":
    main()
