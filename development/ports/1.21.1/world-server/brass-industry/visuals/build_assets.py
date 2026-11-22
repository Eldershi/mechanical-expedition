#!/usr/bin/env python3
"""Draw the industrial controller panels and export their Minecraft assets."""

import argparse
from io import BytesIO
import json
from math import cos, pi
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageDraw

from alloy_furnace import add_console_art, console_model, console_screen

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "overlay/kubejs/assets"
NS = "expedition_industry"
CREATE = "create:block/"
DECO = "createdeco:block/palettes/"
METAL = "#333b3d"
EDGE = "#13191b"
STEEL = "#9bafb2"
STEEL_LIGHT = "#d4e0d3"
BRASS = "#a97743"
GOLD = "#dfb36b"
COPPER = "#b66b4c"
TEAL = "#69b9b2"
IVORY = "#ffe6a6"
INK = "#211c1a"
FACES = ("down", "up", "north", "south", "west", "east")

# Shell, top cover, accent, observation cartridge, fluid output.
CONTROLLERS = {
    "alloy_furnace": ("industrial_iron_block", "industrial_iron_block_top", "copper_casing", "alloy", True),
    "hydropress": ("andesite_casing", "industrial_iron_block_top", "brass_casing", "press", False),
    "shaft_furnace": ("railway_casing", "railway_casing_side", "industrial_iron_block", "shaft", True),
    "electrolytic_cell": ("copper_casing", "copper_casing", "brass_casing", "cell", True),
    "trading_station": ("brass_casing", "brass_casing", "copper_casing", "trade", False),
}
STATE_LIGHT = {"base": "#a45a4d", "ready": "#83a571", "waiting": "#f3a650", "suspend": "#776f64"}

TRANSLATIONS = {
    "en_us": ("Items in", "Items out", "Fluid in", "Fluid out", "Goods / payment",
              "Delivery / payout", "Energy", "Inventory"),
    "zh_cn": ("物品输入", "物品输出", "流体输入", "流体输出", "货物／付款",
              "取货／结算", "电量", "物品栏"),
}
TRANSLATION_KEYS = ("item_input", "item_output", "fluid_input", "fluid_output",
                    "trade_input", "trade_output", "power", "inventory")


def encoded_json(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


class Export:
    def __init__(self):
        self.files = {}

    def json(self, namespace, path, value):
        self.files[f"{namespace}/{path}.json"] = encoded_json(value)

    def png(self, namespace, path, image):
        content = BytesIO()
        image.save(content, "PNG")
        self.files[f"{namespace}/textures/{path}.png"] = content.getvalue()

    def animated(self, path, frames, timing):
        strip = Image.new("RGBA", (16, 16 * len(frames)))
        for i, frame in enumerate(frames):
            strip.paste(frame, (0, i * 16))
        self.png(NS, path, strip)
        self.files[f"{NS}/textures/{path}.png.mcmeta"] = encoded_json({
            "animation": {"frametime": timing, "interpolate": False},
        })


def surface(draw, bounds, face, light, shadow):
    x0, y0, x1, y1 = bounds
    draw.rectangle(bounds, fill=face)
    draw.line((x0, y0, x1, y0), fill=light)
    draw.line((x0, y0, x0, y1), fill=light)
    draw.line((x1, y0 + 1, x1, y1), fill=shadow)
    draw.line((x0 + 1, y1, x1, y1), fill=shadow)


def cartridge(kind, phase, state):
    """One pixel-exact face with an inspection window and a status lamp."""
    active = phase is not None
    t = phase or 0
    img = Image.new("RGBA", (16, 16))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 15, 15), fill=EDGE)
    surface(d, (0, 0, 15, 12), "#524741", "#917460", "#292421")
    for x in (1, 14):
        d.point((x, 1), GOLD)
        d.point((x, 11), BRASS)
    d.rectangle((2, 2, 13, 10), fill="#704b36")
    d.line((2, 2, 13, 2), fill=GOLD)
    d.line((2, 2, 2, 10), fill=BRASS)
    d.rectangle((3, 3, 12, 9), fill=EDGE)
    d.line((3, 9, 12, 9), fill="#3b3b36")

    if kind in ("alloy", "shaft"):
        if kind == "shaft":
            for x in range(4, 13, 3):
                d.line((x, 3, x, 8), fill="#57575b")
        else:
            d.line((4, 8, 11, 8), fill=METAL, width=2)
        for x in range(4, 12):
            height = 1 + ((x * 7 + t * 3) % 5) if active else 0
            if height:
                d.line((x, 8, x, 9 - height), fill=("#ca503b", "#f58d42", "#ffd480")[(x + t) % 3])
        d.line((4, 9, 11, 9), fill="#eb9d54" if active else "#504037")
    elif kind == "press":
        depth = round(3 * (1 - cos(2 * pi * t / 8)) / 2) if active else 0
        for x in (4, 11):
            d.line((x, 3, x, 8), fill=BRASS)
            d.point((x, 3), GOLD)
        d.rectangle((7, 3, 8, 4 + depth), fill=STEEL)
        d.rectangle((5, 4 + depth, 10, 5 + depth), fill=STEEL_LIGHT)
        d.line((5, 5 + depth, 10, 5 + depth), fill="#74878b")
        d.line((5, 9, 10, 9), fill=BRASS)
    elif kind == "cell":
        d.rectangle((4, 5, 11, 8), fill="#276365" if active else "#224044")
        d.line((4, 5, 11, 5), fill=TEAL)
        for x in (6, 9):
            d.line((x, 3, x, 7), fill=("#95716a" if active else "#64534c"))
        if active:
            for x, offset in ((5, 0), (7, 3), (8, 5), (10, 1)):
                y = 8 - ((t + offset) % 6)
                d.point((x, y), "#bcfff0" if y > 4 else TEAL)
    else:
        shutter = round(4 * (1 + cos(2 * pi * t / 8)) / 2) if active else 4
        if active:
            x = 4 + t % 5
            d.rectangle((x, 7, x + 2, 8), fill=GOLD, outline=BRASS)
            d.point((x + 1, 7), IVORY)
        for row in range(shutter):
            d.line((4, 3 + row, 11, 3 + row), fill=(STEEL, METAL)[row % 2])
        d.line((4, 9, 11, 9), fill=GOLD)
    d.rectangle((1, 13, 14, 15), fill="#2c2723")
    d.line((2, 13, 7, 13), fill="#776456")
    d.line((8, 13, 11, 13), fill="#53463d")
    d.rectangle((12, 13, 13, 14), fill=("#a5f0ab" if active else STATE_LIGHT[state]))
    return img


def hollow_socket(draw, x, y, edge, shape):
    if shape == "round":
        draw.polygon([(x + 1, y), (x + 3, y), (x + 4, y + 1), (x + 4, y + 3),
                      (x + 3, y + 4), (x + 1, y + 4), (x, y + 3), (x, y + 1)], fill=edge)
        draw.rectangle((x + 1, y + 1, x + 3, y + 3), fill=EDGE)
    else:
        surface(draw, (x, y, x + 4, y + 4), EDGE, edge, "#1b1717")


def ports(fluid_in, fluid_out):
    image = Image.new("RGBA", (16, 16))
    draw = ImageDraw.Draw(image)
    surface(draw, (0, 0, 15, 15), "#5d5148", "#a0876c", "#302823")
    surface(draw, (1, 1, 14, 14), METAL, EDGE, "#837064")
    hollow_socket(draw, 2, 2, STEEL, "square")
    draw.line((3, 4, 5, 4), fill=STEEL_LIGHT)
    hollow_socket(draw, 9, 2, GOLD, "square")
    draw.line((10, 5, 12, 3), fill=IVORY)
    draw.point((11, 4), GOLD)
    if fluid_in:
        hollow_socket(draw, 2, 9, COPPER, "round")
        draw.line((4, 10, 4, 12), fill=TEAL)
    if fluid_out:
        hollow_socket(draw, 9, 9, COPPER, "round")
        draw.line((11, 10, 12, 11, 11, 12), fill=GOLD)
    elif not fluid_in:
        for y in (9, 11, 13):
            draw.line((3, y, 12, y), fill=EDGE)
    return image


def element(start, end, textures, *, uv=None, rotation=None, cull=False):
    if isinstance(textures, str):
        textures = dict.fromkeys(FACES, textures)
    out = {"from": start, "to": end, "faces": {}}
    for face, texture in textures.items():
        data = {"texture": texture}
        if uv and face in uv:
            data["uv"] = uv[face]
        if cull:
            data["cullface"] = face
        out["faces"][face] = data
    if rotation:
        out["rotation"] = rotation
    return out


def socket_plate(start, end, face):
    textures = {**dict.fromkeys(FACES, "#shell"), face: "#jacks"}
    return element(start, end, textures, uv={face: [0, 0, 16, 16]})


def cover(y, face, skin):
    # Recess the jack surround while keeping the edges on the original block boundary.
    slices = ((0, 0, 16, 3), (0, 13, 16, 16), (0, 3, 3, 13), (13, 3, 16, 13))
    return [
        *(element([x0, y, z0], [x1, y + 1, z1], skin) for x0, z0, x1, z1 in slices),
        socket_plate([3, y, 3], [13, y + 1, 13], face),
    ]


def controller_model(shell, roof, accent, skin, face):
    textures = {"particle": CREATE + shell, "shell": CREATE + shell, "roof": CREATE + roof,
                "accent": CREATE + accent, "jacks": f"{NS}:block/works/ports_{skin}",
                "strip": f"{NS}:block/works/strip_{skin}", "screen": f"{NS}:block/works/{face}"}
    return {
        "parent": "minecraft:block/block",
        "textures": textures,
        "elements": [
            element([1, 0, 1], [15, 16, 15], {"south": "#shell",
                                             "west": "#shell", "east": "#shell"}),
            *cover(0, "down", "#shell"),
            *cover(15, "up", "#roof"),
            element([0, 1, 0], [1, 15, 16], {"north": "#accent", "south": "#shell"}),
            element([15, 1, 0], [16, 15, 16], {"north": "#accent", "south": "#shell"}),
            element([1, 5, 1], [15, 15, 2], {"north": "#screen"}, uv={"north": [1, 2, 15, 16]}),
            element([1, 1, 0], [15, 5, 1], {"north": "#strip"}, uv={"north": [1, 0, 15, 4]}),
            element([1, 5, 0], [15, 6, 1], {"north": "#accent", "up": "#accent"}),
            socket_plate([3, 3, 15], [13, 13, 16], "south"),
            socket_plate([0, 3, 3], [1, 13, 13], "west"),
            socket_plate([15, 3, 3], [16, 13, 13], "east"),
        ],
    }


def port_strip(fluid_in, fluid_out):
    image = Image.new("RGBA", (16, 16), EDGE)
    draw = ImageDraw.Draw(image)
    draw.point((2, 0), STEEL)
    draw.rectangle((2, 1, 4, 3), outline=STEEL)
    draw.line((6, 3, 8, 0), fill=GOLD)
    if fluid_in:
        draw.rectangle((9, 1, 11, 3), outline=COPPER)
        draw.point((10, 2), TEAL)
    if fluid_out:
        draw.rectangle((12, 1, 14, 3), outline=COPPER)
        draw.point((13, 2), GOLD)
    return image


def add_controller(export, name, shell, roof, accent, kind, fluid_out):
    fluid_in = kind != "trade"
    skin = "full" if fluid_out else "in" if fluid_in else "item"
    base = console_model(element) if kind == "alloy" else controller_model(shell, roof, accent, skin, f"{kind}_base")
    screen = console_screen if kind == "alloy" else lambda state, frame=None: cartridge(kind, frame, state)
    export.json(NS, f"models/block/{name}", base)
    export.png(NS, f"gui/works/{kind}", screen("working", 3))
    for state in STATE_LIGHT:
        export.png(NS, f"block/works/{kind}_{state}", screen(state))
    export.animated(f"block/works/{kind}_working", [screen("working", i) for i in range(8)],
                    3 if kind == "press" else 2)
    for state in ("ready", "working", "waiting", "suspend"):
        export.json(NS, f"models/block/works/{name}_{state}", {
            "parent": f"{NS}:block/{name}", "textures": {"screen": f"{NS}:block/works/{kind}_{state}"},
        })


def cube(textures):
    if isinstance(textures, str):
        textures = {"all": textures}
        return {"parent": "minecraft:block/cube_all", "textures": textures}
    return {"parent": "minecraft:block/cube", "textures": {**textures, "particle": textures["north"]}}


def variants(export, name, values):
    export.json("design_decor", f"blockstates/{name}", {
        "variants": {value: {"model": f"design_decor:block/{name}", **rotation}
                     for value, rotation in values.items()},
    })


def put_decor(export, name, model):
    export.json("design_decor", f"models/block/{name}", model)


def ported_boiler(export, name, metal, shell, oriented):
    firing = CREATE + "fluid_tank_top"
    if metal == "iron":
        firing = DECO + "hull/industrial_iron_hull_front"
    rim = CREATE + shell
    side = DECO + f"hull/{'industrial_iron' if metal == 'iron' else ('brass' if metal == 'gold' else metal)}_hull_side"
    if name.endswith("_structure"):
        put_decor(export, name, cube(side))
    elif oriented:
        faces = dict.fromkeys(FACES, side)
        faces.update(north=firing, south=rim)
        put_decor(export, name, cube(faces))
        variants(export, name, {
            "facing=north": {}, "facing=east": {"y": 90}, "facing=south": {"y": 180},
            "facing=west": {"y": 270}, "facing=up": {"x": 270}, "facing=down": {"x": 90},
        })
    else:
        faces = dict.fromkeys(FACES, side)
        faces.update(up=firing, down=rim)
        put_decor(export, name, cube(faces))


def add_decor(export):
    for name, metal, texture, oriented in (
        ("industrial_iron", "iron", "industrial_iron_block", True),
        ("brass", "brass", "brass_casing", False),
        ("gold", "gold", "brass_block", False),
    ):
        for suffix in ("", "_large", "_structure"):
            ported_boiler(export, f"{name}_boiler{suffix}", metal, texture, oriented and not suffix)
    ported_boiler(export, "copper_boiler", "copper", "copper_casing", True)

    put_decor(export, "industrial_plating_block", cube(DECO + "sheet_metal/industrial_iron_sheet_metal"))
    put_decor(export, "industrial_gold_block", cube(DECO + "sheet_metal/brass_sheet_metal"))
    put_decor(export, "metal_support", cube(DECO + "support/industrial_iron_support"))
    support = Image.new("RGBA", (16, 16), "#333d40")
    d = ImageDraw.Draw(support)
    for x in (0, 15):
        d.line((x, 0, x, 15), fill="#505b5c")
    d.polygon([(0, 12), (12, 0), (15, 0), (15, 3), (3, 15), (0, 15)], fill="#798687")
    d.line((0, 12, 12, 0), fill="#a4b1a9", width=1)
    d.line((3, 15, 15, 3), fill="#4e5b5f", width=1)
    for xy in ((1, 14), (14, 1), (8, 8)):
        d.point(xy, "#dae0cc")
    export.png(NS, "block/works/brace", support)
    reverse = support.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    export.png(NS, "block/works/brace_reverse", reverse)
    for name in ("diagonal_girder", "diagonal_metal_support"):
        faces = dict.fromkeys(FACES, DECO + "sheet_metal/industrial_iron_sheet_metal_connected")
        faces.update(east=f"{NS}:block/works/brace", west=f"{NS}:block/works/brace_reverse")
        put_decor(export, name, cube(faces))
        rotations = dict(north=0, east=90, south=180, west=270)
        if name == "diagonal_girder":
            variants(export, name, {
                f"facing={face},facing_up={str(up).lower()}": {"x": 0 if up else 180, "y": angle}
                for face, angle in rotations.items() for up in (False, True)
            })
        else:
            variants(export, name, {f"facing={face}": {"y": angle} for face, angle in rotations.items()})

    for lamp, frame, casing in (("andesite_floodlight", "andesite", "andesite_casing"),
                                ("brass_lamp", "brass", "brass_casing")):
        skin = f"{NS}:block/works/{lamp}"
        lamp_image = Image.new("RGBA", (16, 16))
        draw = ImageDraw.Draw(lamp_image)
        surface(draw, (0, 0, 15, 15), "#583e2b" if frame == "brass" else "#444b49", GOLD, EDGE)
        draw.rectangle((3, 3, 12, 12), fill="#cf8a43")
        draw.rectangle((4, 4, 11, 11), fill=IVORY)
        for x in (3, 7, 8, 12):
            draw.line((x, 3, x, 12), fill="#71604a")
        export.png(NS, f"block/works/{lamp}", lamp_image)
        model = cube({**dict.fromkeys(FACES, CREATE + casing), "north": skin})
        put_decor(export, lamp, model)
        variants(export, lamp, {
            "facing=north": {}, "facing=east": {"y": 90}, "facing=south": {"y": 180},
            "facing=west": {"y": 270}, "facing=up": {"x": 270}, "facing=down": {"x": 90},
        })

    gear = dict.fromkeys(FACES, CREATE + "encased_chain_drive_middle")
    gear.update(up=CREATE + "gearbox_top", down=CREATE + "gearbox_top")
    put_decor(export, "industrial_gear_large", cube(gear))
    variants(export, "industrial_gear_large", {"axis=y": {}, "axis=x": {"x": 90, "y": 90},
                                                        "axis=z": {"x": 90}})
    grate = Image.new("RGBA", (16, 16), "#1c2528")
    d = ImageDraw.Draw(grate)
    for axis in (1, 4, 7, 10, 13):
        d.line((axis, 0, axis, 15), fill="#687779")
        d.line((0, axis, 15, axis), fill="#455354")
        d.point((axis, 1), STEEL)
    d.rectangle((0, 0, 15, 15), outline="#87918d")
    export.png(NS, "block/works/grate", grate)
    put_decor(export, "ornate_grate", cube(f"{NS}:block/works/grate"))

    for rail, metal in (("iron_railing", "industrial_iron"), ("copper_railing", "copper")):
        texture = DECO + f"sheet_metal/{metal}_sheet_metal"
        for suffix, parent in (("_post", "fence_post"), ("_side", "fence_side"), ("_inventory", "fence_inventory")):
            put_decor(export, rail + suffix, {"parent": f"minecraft:block/{parent}", "textures": {"texture": texture}})
    slab = "brass_brick_slab"
    surface_path = f"{NS}:block/works/firebrick"
    brick = Image.new("RGBA", (16, 16), "#594031")
    d = ImageDraw.Draw(brick)
    for y in (0, 4, 8, 12):
        for x in range(-4 if y % 8 else 0, 16, 8):
            surface(d, (x, y, x + 7, y + 3), "#bd8750", "#d4a565", "#744c36")
    export.png(NS, "block/works/firebrick", brick)
    for suffix, parent in (("", "slab"), ("_top", "slab_top"), ("_double", "cube_all")):
        export.json("create_things_and_misc", f"models/block/{slab}{suffix}",
                    {"parent": f"minecraft:block/{parent}",
                     "textures": dict.fromkeys(("bottom", "top", "side") if suffix != "_double" else ("all",),
                                               surface_path)})
    carbon = dict.fromkeys(FACES, CREATE + "dark_metal_block")
    carbon.update(up=DECO + "hull/copper_hull_front", down=DECO + "hull/copper_hull_front")
    export.json("expedition_space", "models/block/carbon_electrode", cube(carbon))


def add_moving_parts(export):
    parts = {
        "press_yoke": ({"casing": CREATE + "brass_casing", "beam": CREATE + "girder",
                        "rod": CREATE + "mechanical_press_pole"}, [
            element([4, 11, 6], [12, 15, 16], "#beam"),
            element([4, 8, 3], [12, 13, 10], "#casing"),
            element([7, 5, 5], [9, 10, 8], "#rod"),
        ]),
        "trade_counter": ({"frame": CREATE + "brass_casing", "bed": CREATE + "depot_top",
                            "runner": CREATE + "girder"}, [
            element([4, 0, 10], [12, 1, 16], "#bed"),
            element([3, 0, 9], [4, 2, 16], "#runner"),
            element([12, 0, 9], [13, 2, 16], "#runner"),
            element([5, 0, 9], [11, 1, 10], "#frame"),
        ]),
        "parcel": ({"paper": CREATE + "packager_particle", "straps": CREATE + "brass_block"}, [
            element([6, 0, 11], [10, 4, 15], "#paper"),
            element([7, 4, 11], [8, 5, 15], "#straps"),
        ]),
    }
    for name, (textures, elements) in parts.items():
        export.json(NS, f"models/block/works/{name}",
                    {"parent": "minecraft:block/block", "textures": textures, "elements": elements})


def add_items(export):
    credit = Image.new("RGBA", (16, 16))
    d = ImageDraw.Draw(credit)
    coin = [(5, 2), (10, 2), (13, 5), (13, 10), (10, 13), (5, 13), (2, 10), (2, 5)]
    d.polygon(coin, fill="#ad6e39", outline="#493223")
    d.polygon([(5, 3), (10, 3), (12, 5), (12, 9), (10, 11), (5, 11), (3, 9), (3, 5)],
              fill=GOLD, outline="#efcb7d")
    d.line((6, 5, 9, 5, 9, 7, 6, 7, 6, 9, 9, 9), fill="#835937")
    d.line((5, 12, 10, 12), fill="#9a5d31")
    steel = Image.new("RGBA", (16, 16))
    d = ImageDraw.Draw(steel)
    d.polygon([(2, 9), (6, 5), (12, 4), (14, 6), (13, 10), (8, 13), (3, 12)],
              fill="#4d5659", outline=EDGE)
    d.polygon([(2, 9), (6, 5), (12, 4), (14, 6), (11, 8), (6, 10)],
              fill=STEEL, outline="#596467")
    d.line((4, 8, 7, 6, 11, 5), fill=STEEL_LIGHT)
    d.line((5, 10, 10, 9, 13, 7), fill="#78898a")
    d.point((7, 8), "#775d46")
    d.point((9, 6), "#8e7963")
    for name, icon in (("trade_credit", credit), ("semi_finished_steel", steel)):
        export.png(NS, f"item/works/{name}", icon)
        export.json(NS, f"models/item/{name}", {
            "parent": "minecraft:item/generated",
            "textures": {"layer0": f"{NS}:item/works/{name}"},
        })


def add_gui(export):
    def png(path, size, paint):
        img = Image.new("RGBA", size)
        paint(ImageDraw.Draw(img))
        export.png(NS, f"gui/works/{path}", img)

    def panel(draw):
        surface(draw, (0, 0, 217, 193), "#cbb596", "#4d3a2f", "#3d2b25")
        surface(draw, (2, 2, 215, 191), "#d5c3a6", "#f3e2c0", "#9e8062")
        draw.rectangle((4, 4, 213, 189), outline="#a98d6e")
        for x, y in ((4, 4), (213, 4), (4, 189), (213, 189)):
            draw.point((x, y), INK)
    png("panel", (218, 194), panel)

    def header(draw):
        surface(draw, (0, 0, 203, 23), "#594035", "#936846", "#392620")
        draw.line((1, 21, 202, 21), fill="#c29158")
        for x in (2, 201):
            draw.point((x, 3), GOLD)
            draw.point((x, 20), "#7d5439")
    png("header", (204, 24), header)

    for medium, edge in (("item", "#786754"), ("fluid", "#605547")):
        for direction, mark in (("input", TEAL), ("output", GOLD)):
            def slot(draw):
                surface(draw, (0, 0, 17, 17), "#796d60", "#574333", "#f2e0bb")
                surface(draw, (1, 1, 16, 16), "#555352" if medium == "item" else "#263439", edge, "#413b33")
                draw.line((3, 16, 14, 16), fill=mark)
            png(f"{medium}_{direction}", (18, 18), slot)

    for state, fill in (("empty", "#665546"), ("fill", GOLD)):
        def arrow(draw):
            draw.polygon([(1, 4), (13, 4), (13, 0), (22, 6), (13, 12), (13, 8), (1, 8)],
                         fill=fill, outline=INK)
            draw.line((2, 5, 13, 5), fill="#aa8053" if state == "empty" else IVORY)
        png(f"arrow_{state}", (23, 13), arrow)

        def energy(draw):
            surface(draw, (0, 0, 138, 12), "#443b33" if state == "empty" else "#b27c36", "#8a6243", INK)
            if state == "fill":
                draw.line((2, 2, 136, 2), fill=IVORY)
                draw.line((2, 9, 136, 9), fill=GOLD)
                for x in range(5, 136, 7):
                    draw.line((x, 4, x, 8), fill="#ba8548")
        png(f"power_{state}", (139, 13), energy)
    export.files[f"{NS}/lss/works.lss"] = (HERE / "works.lss").read_bytes()

    for language, values in TRANSLATIONS.items():
        translations = json.loads((ASSETS / NS / "lang" / f"{language}.json").read_text(encoding="utf-8"))
        translations.update({f"gui.{NS}.{key}": value for key, value in zip(TRANSLATION_KEYS, values, strict=True)})
        export.json(NS, f"lang/{language}", translations)


def assemble():
    export = Export()
    for name, params in CONTROLLERS.items():
        add_controller(export, name, *params)
    for skin, fluid_in, fluid_out in (("full", True, True), ("in", True, False), ("item", False, False)):
        export.png(NS, f"block/works/ports_{skin}", ports(fluid_in, fluid_out))
        export.png(NS, f"block/works/strip_{skin}", port_strip(fluid_in, fluid_out))
    add_decor(export)
    add_console_art(export)
    add_moving_parts(export)
    add_items(export)
    add_gui(export)
    return export.files


def verify_donors(files, archives):
    native = set()
    for path in archives:
        with ZipFile(path) as jar:
            native.update(jar.namelist())
    for path, blob in files.items():
        if path.endswith(".json"):
            textures = json.loads(blob).get("textures", {}).values()
        elif path.endswith(".mtl"):
            textures = (line.removeprefix("map_Kd ") for line in blob.decode().splitlines()
                        if line.startswith("map_Kd "))
        else:
            continue
        for donor in textures:
            if donor.startswith(("create:", "createdeco:", "createcraftedbeginning:")):
                ns, tex = donor.split(":")
                assert f"assets/{ns}/textures/{tex}.png" in native, (path, donor)


def apply(files, target, check):
    failures = []
    for path, content in files.items():
        output = target / path
        if output.is_file() and output.read_bytes() == content:
            continue
        if check:
            failures.append(path)
        else:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
    if failures:
        raise SystemExit("Visual assets differ:\n" + "\n".join(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ASSETS)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--donor", type=Path, action="append", default=[])
    opts = parser.parse_args()
    files = assemble()
    if opts.donor:
        verify_donors(files, opts.donor)
    apply(files, opts.output, opts.check)
    print(f"{len(files)} industrial visual assets")


if __name__ == "__main__":
    main()
