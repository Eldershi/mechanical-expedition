"""Build the Forge and NeoForge resource packs from locally installed mod JARs."""

import argparse
from dataclasses import dataclass
from io import BytesIO
import json
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from PIL import Image

CREATE_BRICK = "assets/create/textures/block/palettes/stone_types/brick/scorchia_cut_brick.png"
CREATE_SMALL_BRICK = "assets/create/textures/block/palettes/stone_types/small_brick/scorchia_cut_small_brick.png"
SMELTERY = "block/smeltery/"
FOUNDRY = "block/foundry/"
FOUNDRY_TABLE_PLATE = FOUNDRY + "casting/table_plate"
FOUNDRY_COVERED_PLATE = FOUNDRY + "casting/table_plate_covered"
INDUSTRIAL_IRON = "assets/create/textures/block/industrial_iron_block"
BRICKS = "seared/bricks"
FANCY_BRICKS = "seared/fancy_bricks"
GLASS = "seared_glass"
PANE_FAMILIES = {SMELTERY: GLASS, FOUNDRY: "glass"}
PANE_MODELS = ("pane_post", "pane_side", "pane_side_alt",
               "pane_noside", "pane_noside_alt", "pane_noside_edge")
SCORIA = "assets/create/textures/block/palettes/stone_types/"
SCORCHED_BRICKS = "scorched/bricks"
FOUNDRY_STONE_TEXTURES = {
    SCORCHED_BRICKS: "small_brick/scoria_cut_small_brick",
    "scorched/stone_top": "scoria",
    "scorched/stone_side": "cut/scoria_cut",
    "scorched/polished_side": "polished/scoria_cut_polished",
    "scorched/polished_top": "cap/scoria_cut_cap",
    "scorched/road": "layered/scoria_cut_layered",
    "scorched/chiseled": "alternatives/scoria_cut_indented",
}
FOUNDRY_BRICK_BACKGROUNDS = (
    "controller/foundry_", "controller/alloyer_side",
    "io/chute_", "io/drain_", "io/duct_",
    "tank/fuel_tank", "tank/ingot_tank",
)
SCORCHED_STONE_COLORS = {
    (25, 20, 17): (46, 30, 38),
    (36, 29, 25): (58, 41, 42),
    (45, 35, 29): (62, 44, 50),
    (50, 39, 32): (68, 51, 48),
    (62, 48, 41): (73, 58, 51),
    (72, 58, 50): (78, 62, 54),
    (83, 69, 60): (89, 71, 62),
    (102, 85, 74): (108, 87, 76),
}

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


@dataclass(frozen=True)
class GlassColors:
    edges: tuple
    reflection: tuple
    pane_edge: tuple


SMELTERY_GLASS = GlassColors(
    ((34, 39, 37), (22, 26, 26), (70, 82, 74), (50, 59, 54)),
    ((57, 69, 65), (83, 100, 93)),
    ((65, 76, 69), (30, 35, 33)),
)
FOUNDRY_GLASS = GlassColors(
    ((62, 44, 50), (46, 30, 38), (89, 71, 62), (73, 58, 51)),
    ((84, 66, 58), (108, 87, 76)),
    ((89, 71, 62), (58, 41, 42)),
)

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
    return f"assets/{namespace}/textures/{name}.png"


def read_png(jar, path):
    with Image.open(BytesIO(jar.read(path))) as image:
        return image.convert("RGBA")


def encode_png(image):
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def remap_surface(image, stone_colors, metal_colors=None, bricks=None):
    result = image.copy()
    metal_colors = metal_colors or {}

    for y in range(image.height):
        for x in range(image.width):
            pixel = image.getpixel((x, y))
            rgb, alpha = pixel[:3], pixel[3]
            if alpha != 255:
                continue
            if rgb in metal_colors:
                result.putpixel((x, y), (*metal_colors[rgb], alpha))
                continue
            if rgb not in stone_colors:
                continue

            brick_xy = x, y % 16
            if bricks and pixel == bricks[0].getpixel(brick_xy):
                result.putpixel((x, y), bricks[1].getpixel(brick_xy))
            else:
                result.putpixel((x, y), (*stone_colors[rgb], alpha))

    return result


def glass_frame(connections, colors, original=None, pane=False):
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
            if distance < 2:
                color = colors.edges[2 * distance + (side not in "ul")]
                image.putpixel((x, y), (*color, 255))
    if right - left >= 6:
        tip, shine = colors.reflection
        for x, y, color in ((4, 2, tip), (3, 3, shine), (2, 4, shine)):
            image.putpixel((x + left, y), (*color, 255))
    return image


def glass_pane_edge(colors):
    image = Image.new("RGBA", (16, 16))
    light, dark = colors.pane_edge
    for y in range(16):
        image.putpixel((7, y), (*light, 255))
        image.putpixel((8, y), (*dark, 255))
    return image


def build_glass_textures(mod, namespace, area, clear_glass, colors):
    textures = {}
    native = set(mod.namelist())
    for name in (clear_glass, "soul_glass", "tinted_glass"):
        path = area + name
        original = read_png(mod, asset_name(namespace, path)) if name != clear_glass else None
        textures[path] = encode_png(glass_frame("", colors, original))
        if asset_name(namespace, path + "/normal") in native:
            textures[path + "/normal"] = textures[path]
        for connection in CONNECTIONS[1:]:
            textures[f"{path}/{connection}"] = encode_png(glass_frame(connection, colors, original))
        if name != "tinted_glass":
            pane = path + "_pane"
            textures[pane] = encode_png(glass_frame("", colors, original, pane=True))
            for connection in CONNECTIONS[1:]:
                textures[f"{pane}/{connection}"] = encode_png(glass_frame(connection, colors, original, pane=True))
    textures[f"{area}{clear_glass}_top"] = encode_png(glass_pane_edge(colors))
    return textures


def build_seared_textures(mod, create, namespace):
    old_brick = read_png(mod, asset_name(namespace, SMELTERY + BRICKS))
    create_brick = read_png(create, CREATE_BRICK)
    if old_brick.size != (16, 16) or create_brick.size != (16, 16):
        raise ValueError("Expected 16×16 brick textures")

    textures = {
        SMELTERY + BRICKS: create.read(CREATE_BRICK),
        SMELTERY + FANCY_BRICKS: create.read(CREATE_SMALL_BRICK),
    }
    for name in DEVICE_TEXTURES:
        path = SMELTERY + name
        image = read_png(mod, asset_name(namespace, path))
        bricks = (old_brick, create_brick) if name.startswith(BRICK_BACKGROUNDS) or name == "seared/cracked_bricks" else None
        metal = BRASS_COLORS if name.startswith("io/duct_") else ANDESITE_COLORS
        textures[path] = encode_png(remap_surface(image, STONE_COLORS, metal, bricks))
    textures.update(build_glass_textures(mod, namespace, SMELTERY, GLASS, SMELTERY_GLASS))
    return textures


def industrial_panel(source, width, height):
    def coordinates(length):
        rim = 2 if length >= 5 else 1
        interior = length - 2 * rim
        first = (16 - interior) // 2
        return (*range(rim), *range(first, first + interior), *range(16 - rim, 16))

    panel = Image.new("RGBA", (width, height))
    panel.putdata([source.getpixel((x, y)) for y in coordinates(height) for x in coordinates(width)])
    return panel


def build_anvil_base_textures(create):
    side = read_png(create, INDUSTRIAL_IRON + ".png")
    top = read_png(create, INDUSTRIAL_IRON + "_top.png")
    base = Image.new("RGBA", (16, 16))
    base.paste(industrial_panel(top, 12, 12), (0, 0))
    base.paste(industrial_panel(side, 12, 4), (0, 12))

    # Preserve the pedestal's UV layout for the platform, neck and two braces.
    upper = Image.new("RGBA", (16, 16))
    upper.paste(industrial_panel(top, 8, 6), (0, 0))
    for x, y, width, height in ((0, 6, 8, 3), (8, 0, 3, 6), (12, 0, 4, 7), (10, 9, 6, 7)):
        upper.paste(industrial_panel(side, width, height), (x, y))

    return {
        "block/table/scorched_anvil_base": encode_png(base),
        "block/table/scorched_anvil_base_upper": encode_png(upper),
    }


def build_scorched_textures(mod, create, namespace):
    textures = {
        FOUNDRY + target: create.read(f"{SCORIA}{source}.png")
        for target, source in FOUNDRY_STONE_TEXTURES.items()
    }
    textures.update(build_glass_textures(mod, namespace, FOUNDRY, "glass", FOUNDRY_GLASS))
    brick_path = FOUNDRY + SCORCHED_BRICKS
    old_brick = read_png(mod, asset_name(namespace, brick_path))
    with Image.open(BytesIO(textures[brick_path])) as replacement:
        bricks = old_brick, replacement.convert("RGBA")

    prefix = f"assets/{namespace}/textures/{FOUNDRY}"
    surfaces = [
        FOUNDRY + asset.removeprefix(prefix).removesuffix(".png")
        for asset in mod.namelist() if asset.startswith(prefix) and asset.endswith(".png")
    ]
    surfaces.append("item/materials/scorched_brick")
    for path in surfaces:
        if path in textures:
            continue
        image = read_png(mod, asset_name(namespace, path))
        name = path.removeprefix(FOUNDRY)
        shared = bricks if name.startswith(FOUNDRY_BRICK_BACKGROUNDS) else None
        metal = BRASS_COLORS if name.startswith("io/duct_front_") else None
        result = remap_surface(image, SCORCHED_STONE_COLORS, metal, shared)
        if image.tobytes() != result.tobytes():
            textures[path] = encode_png(result)

    with Image.open(BytesIO(textures[FOUNDRY_TABLE_PLATE])) as plate:
        recess = plate.convert("RGBA")
    # The open casting surface has a gold ring visible through the covered model's gutter.
    for offset in range(1, 15):
        inner = min(13, max(2, offset))
        for point, sample in (
            ((offset, 1), (inner, 2)), ((offset, 14), (inner, 13)),
            ((1, offset), (2, inner)), ((14, offset), (13, inner)),
        ):
            recess.putpixel(point, recess.getpixel(sample))
    textures[FOUNDRY_COVERED_PLATE] = encode_png(recess)
    textures.update(build_anvil_base_textures(create))
    return textures


def build_texture_set(mod, create, namespace):
    return build_seared_textures(mod, create, namespace) | build_scorched_textures(mod, create, namespace)


def write_pack(path, mod, namespace, pack_format, textures):
    resources = {"pack.mcmeta": json.dumps({
        "pack": {
            "pack_format": pack_format,
            "description": "Create-style seared smeltery, scorched foundry, and framed glass",
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

    for area, clear_glass in PANE_FAMILIES.items():
        for folder, glass in (("glass", clear_glass), ("soul_glass", "soul_glass")):
            for model in PANE_MODELS:
                target = f"assets/{namespace}/models/{area}{folder}/{model}.json"
                original = json.loads(mod.read(target))
                original["textures"]["pane"] = f"{namespace}:{area}{glass}_pane"
                resources[target] = json.dumps(original, indent=2) + "\n"

    target = f"assets/{namespace}/models/{FOUNDRY}table_covered.json"
    covered_table = json.loads(mod.read(target))
    covered_table["textures"]["top"] = f"{namespace}:{FOUNDRY_COVERED_PLATE}"
    resources[target] = json.dumps(covered_table, indent=2) + "\n"

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
