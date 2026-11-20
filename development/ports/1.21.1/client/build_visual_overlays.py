#!/usr/bin/env python3
"""Build the 1.21.1 compatibility and local hostile-mob overlays."""

import argparse
import json
from pathlib import Path
import re
import struct
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo
import zlib


ENTITY = "assets/minecraft/textures/entity/"
VANILLA_MOBS = (
    "creeper/creeper.png", "creeper/creeper_armor.png",
    "skeleton/skeleton.png", "skeleton/stray.png", "skeleton/stray_overlay.png",
    "skeleton/wither_skeleton.png", "zombie/drowned.png", "zombie/drowned_outer_layer.png",
    "zombie/husk.png", "zombie/zombie.png",
)


def transparent_png(width, height):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(height * (1 + width * 4))))
            + chunk(b"IEND", b""))


def vanilla_mobs(client_jar):
    with ZipFile(client_jar) as source:
        if json.loads(source.read("version.json"))["id"] != "1.21.1":
            raise ValueError("Use the Minecraft 1.21.1 client jar for vanilla textures")
        assets = {ENTITY + name: source.read(ENTITY + name) for name in VANILLA_MOBS}
    assets[ENTITY + "creeper/creeper_e.png"] = transparent_png(64, 32)
    assets[ENTITY + "zombie/zombie_e.png"] = transparent_png(64, 64)
    return assets


def compatibility_assets():
    lower_weight_enchants = {4, 6, 7, 8, 9}
    return {name: json.dumps(data, indent=2).encode() + b"\n" for name, data in {
        "assets/apotheosis/textures/items/gems/mageslayer.png.mcmeta": {
            "animation": {"frametime": 2, "interpolate": False},
        },
        "assets/minecraft/models/item/milk_bucket.json": {
            "parent": "neoforge:item/bucket_drip", "loader": "neoforge:fluid_container", "fluid": "minecraft:milk",
        },
        "assets/minecraft/sounds.json": {
            "block.enchantment_table.use": {
                "replace": True,
                "subtitle": "subtitles.block.enchantment_table.use",
                "sounds": [
                    {"name": f"block/enchantment_table/enchant{number}",
                     "weight": 10 if number in lower_weight_enchants else 12}
                    for number in range(1, 13)
                ],
            },
        },
    }.items()}


def write_pack(output, description, assets, *, filters=()):
    metadata = {"pack": {"pack_format": 34, "description": description}}
    if filters:
        if len({rule["namespace"] for rule in filters}) != 1:
            raise ValueError("Minecraft 1.21.1 combines namespace and path matches independently within a pack")
        # Minecraft searches for a regex match, so require the entire namespace and path.
        metadata["filter"] = {"block": [
            {"namespace": f"^{re.escape(rule['namespace'])}$", "path": f"^(?:{rule['path']})$"}
            for rule in filters
        ]}
    assets["pack.mcmeta"] = json.dumps(metadata).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w") as archive:
        for name, data in sorted(assets.items()):
            entry = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            entry.compress_type = ZIP_DEFLATED
            archive.writestr(entry, data)


def write_compatibility_packs(output):
    write_pack(output, "Expedition resource compatibility", compatibility_assets(), filters=(
        {"namespace": "minecraft", "path": r"optifine/cem/enchanting_book(?:2?\.jem|\.properties)"},
        {"namespace": "minecraft", "path": r"textures/entity/enchanting_table_book_[es]\.png"},
    ))
    write_pack(output.with_name("Expedition-Filter-Masterful-Machinery-1.21.1.zip"),
               "Expedition Masterful Machinery model filter", {}, filters=(
        {"namespace": "mm", "path": r"models/block/.*\.json"},
    ))
    write_pack(output.with_name("Expedition-Filter-Eden-Ring-1.21.1.zip"),
               "Expedition Eden Ring portal texture filter", {}, filters=(
        {"namespace": "edenring", "path": r"textures/block/portal_block_center_[ns]\.png"},
    ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("vanilla-mobs", "compatibility"))
    parser.add_argument("output", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.kind == "vanilla-mobs":
        if not args.source:
            parser.error("--source must be the Minecraft 1.21.1 client jar")
        write_pack(args.output, "Expedition vanilla hostile mobs", vanilla_mobs(args.source))
    else:
        write_compatibility_packs(args.output)


if __name__ == "__main__":
    main()
