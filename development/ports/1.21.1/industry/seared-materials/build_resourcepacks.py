"""Build the Forge and NeoForge resource packs from locally installed mod JARs."""

import argparse
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from PIL import Image

CREATE_BRICK = "assets/create/textures/block/palettes/stone_types/brick/scorchia_cut_brick.png"
CREATE_SMALL_BRICK = "assets/create/textures/block/palettes/stone_types/small_brick/scorchia_cut_small_brick.png"
SMELTERY = "textures/block/smeltery/"
BRICKS = "seared/bricks"
FANCY_BRICKS = "seared/fancy_bricks"
GLASS = "seared_glass"
PANE_FAMILIES = {"glass": GLASS, "soul_glass": "soul_glass"}
PANE_MODELS = ("pane_post", "pane_side", "pane_side_alt",
               "pane_noside", "pane_noside_alt", "pane_noside_edge")

BRICK_BACKGROUNDS = (
    "controller/heater_",
    "controller/melter_side",
    "controller/smeltery_",
    "io/chute_",
    "io/drain_",
    "io/duct_",
    "tank/fuel_tank",
    "tank/ingot_tank",
)

# Stone colors preserve the original recesses and bevels in non-brick surfaces.
STONE_COLORS = {
    (38, 36, 37): (28, 30, 34),
    (49, 47, 45): (35, 37, 42),
    (56, 52, 51): (41, 44, 48),
    (63, 60, 57): (47, 52, 54),
    (79, 74, 71): (54, 60, 59),
    (98, 91, 87): (64, 73, 68),
    (107, 102, 96): (74, 85, 77),
}

# Metal shades shared by Create's andesite casing and mechanical press.
ANDESITE_COLORS = {
    (138, 65, 41): (64, 69, 67),
    (156, 69, 41): (80, 83, 81),
    (193, 90, 54): (96, 99, 95),
    (231, 124, 86): (130, 135, 132),
    (252, 153, 130): (143, 150, 145),
    (251, 195, 182): (168, 179, 171),
}
BRASS_COLORS = {
    (178, 100, 17): (114, 71, 49),
    (220, 150, 19): (158, 105, 71),
    (233, 177, 21): (191, 142, 85),
    (250, 214, 74): (215, 170, 94),
    (253, 245, 95): (238, 193, 104),
    (255, 253, 224): (255, 235, 140),
}
GLASS_REFLECTION = {
    (4, 2): (57, 69, 65, 255),
    (3, 3): (83, 100, 93, 255),
    (2, 4): (83, 100, 93, 255),
}

DEVICE_TEXTURES = (
    "io/back",
    "io/chute_side_active",
    "io/chute_side_inactive",
    "io/chute_top_active",
    "io/chute_top_inactive",
    "io/drain_front_active",
    "io/drain_front_inactive",
    "io/duct_front_active",
    "io/duct_front_inactive",
    "controller/heater_active",
    "controller/heater_inactive",
    "controller/melter_active",
    "controller/melter_inactive",
    "controller/melter_side",
    "controller/smeltery_active",
    "controller/smeltery_inactive",
    "controller/smeltery_unformed",
    "tank/casting_tank",
    "tank/casting_tank_top",
    "tank/fuel_gauge",
    "tank/fuel_tank",
    "tank/gauge_top",
    "tank/ingot_gauge",
    "tank/ingot_tank",
    "tank/tank_top",
    "casting/basin_bottom",
    "casting/basin_side",
    "casting/basin_top",
    "casting/table_bottom",
    "casting/table_side",
    "casting/table_top",
    "channel_in",
    "channel_out",
    "faucet",
    "lantern",
    "seared/cobble",
    "seared/cracked_bricks",
    "seared/ladder",
    "seared/lamp",
    "seared/paver",
    "seared/paver_slab",
    "seared/stone",
    "seared/triangle_bricks",
)

CONNECTIONS = (
    "normal", "u", "d", "l", "r", "ud", "ul", "ur", "dl", "dr",
    "lr", "udl", "udr", "ulr", "dlr", "udlr",
)


def asset_name(namespace, name):
    return f"assets/{namespace}/{SMELTERY}{name}.png"


def read_png(jar, path):
    with Image.open(BytesIO(jar.read(path))) as image:
        return image.convert("RGBA")


def encode_png(image):
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def remap_device(name, image, original_brick, create_brick):
    result = image.copy()
    shared_bricks = name.startswith(BRICK_BACKGROUNDS) or name == "seared/cracked_bricks"
    metal_colors = BRASS_COLORS if name.startswith("io/duct_") else ANDESITE_COLORS

    for y in range(image.height):
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            rgb, alpha = pixel[:3], pixel[3]
            if alpha != 255:
                continue
            if rgb in metal_colors:
                result.putpixel((x, y), (*metal_colors[rgb], alpha))
                continue
            if rgb not in STONE_COLORS:
                continue

            brick_xy = x, y % 16
            if shared_bricks and pixel == original_brick.getpixel(brick_xy):
                result.putpixel((x, y), create_brick.getpixel(brick_xy))
            else:
                result.putpixel((x, y), (*STONE_COLORS[rgb], alpha))

    return result


def glass_frame(connections, original=None, pane=False):
    image = Image.new("RGBA", (16, 16))
    fill = original.getpixel((8, 8)) if original else (0, 0, 0, 0)
    # The native pane model stops at its 2-pixel post on an unjoined side.
    left = 7 if pane and "l" not in connections else 0
    right = 8 if pane and "r" not in connections else 15
    for y in range(16):
        for x in range(left, right + 1):
            if original:
                interior = original.getpixel((x, y))
                image.putpixel((x, y), interior if interior[3] < 255 else fill)
            edges = [
                (distance, side)
                for distance, side in ((y, "u"), (x - left, "l"), (15 - y, "d"), (right - x, "r"))
                if side not in connections
            ]
            if not edges:
                continue

            distance, side = min(edges, key=lambda edge: edge[0])
            if distance == 0:
                color = (34, 39, 37) if side in "ul" else (22, 26, 26)
            elif distance == 1:
                color = (70, 82, 74) if side in "ul" else (50, 59, 54)
            else:
                continue
            image.putpixel((x, y), (*color, 255))
    for point, color in GLASS_REFLECTION.items():
        x, y = point
        if right - left >= 6:
            image.putpixel((x + left, y), color)
    return image


def glass_pane_edge():
    image = Image.new("RGBA", (16, 16))
    for y in range(16):
        image.putpixel((7, y), (65, 76, 69, 255))
        image.putpixel((8, y), (30, 35, 33, 255))
    return image


def build_texture_set(mod, create, namespace):
    old_brick = read_png(mod, asset_name(namespace, BRICKS))
    create_brick = read_png(create, CREATE_BRICK)
    if old_brick.size != (16, 16) or create_brick.size != (16, 16):
        raise ValueError("Expected 16×16 brick textures")

    textures = {
        BRICKS: create.read(CREATE_BRICK),
        FANCY_BRICKS: create.read(CREATE_SMALL_BRICK),
    }
    for name in DEVICE_TEXTURES:
        image = read_png(mod, asset_name(namespace, name))
        textures[name] = encode_png(remap_device(name, image, old_brick, create_brick))

    textures[GLASS] = encode_png(glass_frame(""))
    textures[f"{GLASS}_top"] = encode_png(glass_pane_edge())
    for connection in CONNECTIONS:
        textures[f"{GLASS}/{connection}"] = encode_png(
            glass_frame("" if connection == "normal" else connection)
        )
    for glass in ("soul_glass", "tinted_glass"):
        original = read_png(mod, asset_name(namespace, glass))
        textures[glass] = encode_png(glass_frame("", original))
        for connection in CONNECTIONS[1:]:
            textures[f"{glass}/{connection}"] = encode_png(glass_frame(connection, original))
    for glass in PANE_FAMILIES.values():
        original = read_png(mod, asset_name(namespace, glass)) if glass != GLASS else None
        pane = glass + "_pane"
        textures[pane] = encode_png(glass_frame("", original, pane=True))
        for connection in CONNECTIONS[1:]:
            textures[f"{pane}/{connection}"] = encode_png(glass_frame(connection, original, pane=True))

    return textures


def write_pack(path, mod, namespace, pack_format, textures):
    resources = {"pack.mcmeta": json.dumps({
        "pack": {
            "pack_format": pack_format,
            "description": "Create-style seared smeltery and dark framed glass",
        }
    }, indent=2) + "\n"}
    mod_files = set(mod.namelist())
    for name, data in textures.items():
        target = asset_name(namespace, name)
        with Image.open(BytesIO(data)) as replacement:
            if target in mod_files and read_png(mod, target).size != replacement.size:
                raise ValueError(f"Dimension mismatch for {target}")
        resources[target] = data
        if target + ".mcmeta" in mod_files:
            resources[target + ".mcmeta"] = mod.read(target + ".mcmeta")

    for folder, glass in PANE_FAMILIES.items():
        for model in PANE_MODELS:
            target = f"assets/{namespace}/models/block/smeltery/{folder}/{model}.json"
            original = json.loads(mod.read(target))
            original["textures"]["pane"] = f"{namespace}:block/smeltery/{glass}_pane"
            resources[target] = json.dumps(original, indent=2) + "\n"

    with ZipFile(path, "w", compression=ZIP_DEFLATED) as pack:
        for name, data in sorted(resources.items()):
            pack.writestr(ZipInfo(name), data, compress_type=ZIP_DEFLATED)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("forge_tinkers", type=Path)
    parser.add_argument("neoforge_tinkers", type=Path)
    parser.add_argument("forge_create", type=Path)
    args = parser.parse_args()

    destination = Path(__file__).resolve().parent
    with ZipFile(args.forge_tinkers) as forge, ZipFile(args.neoforge_tinkers) as neo, ZipFile(args.forge_create) as create:
        textures = build_texture_set(forge, create, "tconstruct")
        native = set(forge.namelist())
        for name in textures:
            path = asset_name("tconstruct", name)
            if path not in native:
                continue
            left = forge.read(path)
            right = neo.read(asset_name("modernfoundry", name))
            if left != right:
                raise ValueError(f"Original textures are different between versions: {name}")

        write_pack(destination / "Create-Style-Seared-Forge-1.20.1.zip",
                   forge, "tconstruct", 15, textures)
        write_pack(destination / "Create-Style-Seared-NeoForge-1.21.1.zip",
                   neo, "modernfoundry", 34, textures)


if __name__ == "__main__":
    main()
