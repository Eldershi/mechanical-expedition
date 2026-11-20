#!/usr/bin/env python3
"""Build Rock & Stone data for the retained CMI deposit types."""

import argparse
from copy import deepcopy
from gzip import GzipFile
import json
import nbtlib
from pathlib import Path
import shutil
from zipfile import ZipFile


OVERWORLD = "minecraft:overworld"
NETHER = "minecraft:the_nether"
MOON = "ad_astra:moon"
DEPOSITS = {
    "aluminum": (OVERWORLD, "immersiveengineering:raw_aluminum"),
    "vanadium": (NETHER, "cmi:raw_vanadium"),
    "coal": (OVERWORLD, "minecraft:coal"),
    "iron": (OVERWORLD, "minecraft:raw_iron"),
    "platinum": (MOON, "alltheores:platinum_nugget"),
    "cheese": (MOON, "ad_astra:cheese"),
    "oil_shale": (OVERWORLD, "cmi:oil_shale"),
}
NATIVE_BLOCKS = {"coal", "iron"}


def put(root, key, value):
    path = root / key
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def copy_asset(source, target, relative):
    dest = target / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / relative, dest)


def deposit_yields(kind):
    def result(item, chance=1, catalysts=()):
        value = {"items": [{"item": item}], "chance": chance}
        if catalysts:
            value["catalysts"] = list(catalysts)
        return value

    dimension, primary = DEPOSITS[kind]
    base_rock = {OVERWORLD: "minecraft:cobblestone", NETHER: "minecraft:netherrack", MOON: "ad_astra:moon_stone"}
    overclock = "expedition:vanadium_overclock" if kind == "vanadium" else "create_rns:overclock"
    yields = [result(base_rock[dimension]), result("create_rns:resonant_amethyst", 0.0005, (overclock,))]
    if kind == "vanadium":
        yields.append(result("cmi:nether_vanadium_ore", 0.30,
                             ("create_rns:shattering_resonance", "expedition:vanadium_overclock")))
    elif kind == "platinum":
        for tier, chance in (("faint_resonance", 0.05), ("resonance", 0.50)):
            yields.append(result(primary, chance, (f"create_rns:{tier}", "create_rns:overclock")))
    elif kind in {"cheese", "coal"}:
        yields.append(result(primary, 0.5, ("create_rns:overclock",)))
    else:
        yields.append(result(primary, 0.30, ("create_rns:shattering_resonance", "create_rns:overclock")))
        if kind == "aluminum":
            yields.append(result(primary, 0.20, ("create_rns:resonance", "create_rns:overclock")))
    return yields


def register_deposit_data(data, kind):
    dimension, icon = DEPOSITS[kind]
    node = f"cmi:ore_node/{kind}_node"
    put(data, f"expedition/create_rns/deposit_spec/legacy_{kind}.json", {
        "scanner_icon_item": icon,
        "map_icon_item": icon,
        "structure": node,
        "dimension": dimension,
        "scannable": kind == "vanadium",
    })
    block = f"cmi:{kind}_deposit_block"
    if kind not in NATIVE_BLOCKS or kind == "coal":
        put(data, f"expedition/recipe/deposits/{kind}.json", {
            "type": "create_rns:mining",
            "deposit_block": block,
            "dimension": dimension,
            "durability": {"core": 200000, "edge": 75000, "random_spread": 0.2},
            "replace_when_depleted": "create_rns:depleted_deposit_block",
            "yields": deposit_yields(kind),
        })


def register_structure(source, data, kind):
    def pool_element(location, weight):
        return {"weight": weight, "element": {
            "location": location, "element_type": "minecraft:single_pool_element",
            "processors": "minecraft:empty", "projection": "rigid",
        }}

    path = f"ore_node/{kind}_node"
    structure = {
        "type": "minecraft:jigsaw",
        "biomes": [],
        "size": 2,
        "start_pool": f"cmi:{path}",
        "step": "surface_structures",
        "start_height": {"absolute": 0},
        "project_start_to_heightmap": "WORLD_SURFACE_WG",
        "spawn_overrides": {},
        "max_distance_from_center": 64,
        "terrain_adaptation": "beard_thin",
        "use_expansion_hack": False,
    }
    if kind == "vanadium":
        structure.update({
            "biomes": "#minecraft:is_nether",
            "step": "underground_structures",
            "start_height": {"type": "minecraft:uniform", "min_inclusive": {"absolute": -96},
                             "max_inclusive": {"absolute": -10}},
        })
        put(data, "cmi/worldgen/structure_set/vanadium_deposits.json", {
            "placement": {"type": "minecraft:random_spread", "salt": 395602385, "spacing": 20, "separation": 15},
            "structures": [{"structure": f"cmi:{path}", "weight": 1}],
        })
    put(data, f"cmi/worldgen/structure/{path}.json", structure)
    put(data, f"cmi/worldgen/template_pool/{path}.json", {
        "fallback": "minecraft:empty", "elements": [pool_element(f"cmi:{path}", 1)],
    })
    depot = []
    for size, weight in (("large", 2), ("medium", 2), ("small", 3)):
        part = f"deposit/{kind}/{size}"
        if (source / f"data/cmi/structures/{part}.nbt").is_file():
            copy_template(source, data, part)
            depot.append(pool_element(f"cmi:{part}", weight))
    if depot:
        put(data, f"cmi/worldgen/template_pool/deposit_{kind}.json", {"fallback": "minecraft:empty", "elements": depot})
    copy_template(source, data, path)


def copy_template(source, data, template):
    origin = source / f"data/cmi/structures/{template}.nbt"
    if not origin.is_file():
        raise FileNotFoundError(origin)
    dest = data / f"cmi/structure/{template}.nbt"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if template in {"ore_node/platinum_node", "ore_node/cheese_node"}:
        structure = nbtlib.load(origin)
        for state in structure["palette"]:
            if state["Name"] in {"cmi:platinum_ore_node", "cmi:cheese_ore_node"}:
                state["Name"] = nbtlib.String(str(state["Name"]).replace("_ore_node", "_deposit_block"))
        with dest.open("wb") as output:
            with GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
                structure.write(compressed)
    else:
        shutil.copy2(origin, dest)


def model(base, overlay):
    return {"parent": "minecraft:block/block", "loader": "neoforge:composite",
            "textures": {"particle": base}, "children": {
                "base": {"parent": "minecraft:block/cube_all", "textures": {"all": base}},
                "ore": {"parent": "minecraft:block/cube_all", "render_type": "minecraft:cutout",
                        "textures": {"all": overlay}},
            }}


def build(source, target, minecraft):
    data = target / "data"
    put(data, "expedition/create_rns/catalyst/vanadium_overclock.json", {
        "requirements": [{"type": "fluid", "consume": {"id": "minecraft:lava", "amount": 20}}],
        "display_priority": 1004,
        "representative_items": ["minecraft:lava_bucket"],
        "play_when_active": {"sound_id": "create_rns:mining_overclocked_accent"},
    })
    for kind in DEPOSITS:
        register_deposit_data(data, kind)
        register_structure(source, data, kind)
        if kind in NATIVE_BLOCKS and kind != "coal":
            continue
        texture = f"assets/cmi/textures/block/ore/node/{kind}.png"
        copy_asset(source, target, texture)
        put(target, f"assets/cmi/models/block/deposits/{kind}.json", model(
            "create_rns:block/depleted_deposit_block", f"cmi:block/ore/node/{kind}"))

    with ZipFile(minecraft) as game:
        template = json.loads(game.read("data/minecraft/loot_table/blocks/deepslate_diamond_ore.json"))
    for name, base, mineral, drop in (
        ("nether_vanadium_ore", "minecraft:block/netherrack", "vanadium", "cmi:raw_vanadium"),
        ("moon_platinum_ore", "ad_astra:block/moon_stone", "platinum", "alltheores:raw_platinum"),
    ):
        put(target, f"assets/cmi/models/block/deposits/{mineral}_ore.json",
            model(base, f"cmi:block/ore/node/{mineral}"))
        table = deepcopy(template)
        silk, ordinary = table["pools"][0]["entries"][0]["children"]
        silk["name"] = f"cmi:{name}"
        ordinary["name"] = drop
        table["random_sequence"] = f"expedition:blocks/{name}"
        put(data, f"cmi/loot_table/blocks/{name}.json", table)
    copy_asset(source, target, "assets/cmi/textures/block/oil_shale.png")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("minecraft", type=Path)
    args = parser.parse_args()
    build(args.source, args.target, args.minecraft)
