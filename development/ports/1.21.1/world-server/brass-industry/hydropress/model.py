"""Hydraulic press geometry and construction coordinates in sixteenths of a block."""

from collections import Counter, defaultdict
from itertools import product

SIZE = (5, 8, 8)
CORE = (2, 2, 1)
FUNNEL = (0, 2, 3)
CONNECTOR = (4, 2, 6)
STROKE = 29
PORTS = {
    "item_input": {"pos": [1, 2, 3], "faces": ["west"], "io": "IN"},
    "item_output": {"pos": [4, 2, 3], "faces": ["east"], "io": "OUT"},
    "fluid_input": {"pos": [2, 2, 7], "faces": ["south"], "io": "IN"},
    "forge_energy_storage": {"pos": [3, 2, 6], "faces": ["east"], "io": "IN"},
}
GIRDER = "create:metal_girder"
IRON = "create:industrial_iron_block"
CASING = "create:andesite_casing"
PIPE = "create:fluid_pipe"

PARTS = []


def box(name, group, material, bounds, block=IRON, motion="body"):
    PARTS.append(dict(name=name, group=group, material=material,
                      bounds=bounds, block=block, motion=motion))


def beam(name, along, a, b, center, low, high, width=9):
    """Continuous flanges with one slim web, along the long axis of the member."""
    lo, hi = center - width // 2, center + (width + 1) // 2
    for u, y, v, top in ((lo, low, hi, low+2), (center-2, low+2, center+2, high-2),
                         (lo, high-2, hi, high)):
        bounds = (a, y, u, b, top, v) if along == "x" else (u, y, a, v, top, b)
        box(name, "frame", "girder", bounds, GIRDER)


for x in (8, 72):
    for z in (38, 74, 109):
        box("地脚承重板", "frame", "foot", (x-7, 0, z-7, x+7, 3, z+7))
        box("地脚立座", "frame", "frame", (x-4, 3, z-4, x+4, 10, z+4))
    for a,b in (((30,48),(64,117)) if x == 8 else ((30,117),)):
        beam("底架纵梁", "z", a, b, x, 10, 21)
for z in (38, 74, 109):
    beam("底架横梁", "x", 13, 68, z, 10, 21)

# The portal legs leave the complete loading and discharge corridor open.
for x in (8, 72):
    for z in (38, 74):
        box("立柱脚座", "frame", "foot", (x-6, 21, z-6, x+6, 25, z+6))
        box("立柱外翼缘", "frame", "girder", (x-5,25,z-4,x-3,87,z+4), GIRDER)
        box("立柱内翼缘", "frame", "girder", (x+3,25,z-4,x+5,87,z+4), GIRDER)
        box("立柱腹板", "frame", "girder", (x-3,25,z-2,x+3,87,z+2), GIRDER)
        box("柱头节点板", "frame", "foot", (x-6,87,z-6,x+6,92,z+6))
for z in (38, 74):
    beam("龙门横梁", "x", 14, 66, z, 83, 97, 11)
for x in (8, 72):
    beam("门架纵向连梁", "z", 44, 70, x, 85, 98, 11)
beam("缸座前横撑", "z", 44, 70, 29, 87, 97)
beam("缸座后横撑", "z", 44, 70, 51, 87, 97)

box("床身横担", "press", "frame", (17,21,42,63,30,71))
box("模台机座", "press", "frame", (26,29,44,54,35,68))
box("模具底托", "press", "tool", (28,35,47,52,39,65))
# The tool's opening is above the fixture and beneath the ram.
for bounds in ((28,39,47,30,42,65), (50,39,47,52,42,65),
               (30,39,47,50,42,49), (30,39,63,50,42,65)):
    box("模座定位边", "press", "tool", bounds)
for x0, x1 in ((16,28),(52,65)):
    for z in (48,64):
        box("输送台导轨", "items", "tool", (x0,31,z-1,x1,35,z+1))
    box("接料台承托", "items", "frame", (x0,24,48,x1,31,64))
    for x in range(x0+1,x1-1,4):
        box("滚子输送面", "items", "roller", (x,35,49,x+2,39,63))
for z0,z1 in ((47,49),(63,65)):
    box("出料槽侧壁", "items", "frame", (65,31,z0,80,49,z1))
box("出料槽底板", "items", "tool", (65,30,49,80,39,63))
box("出料口上沿", "items", "tool", (65,46,49,80,49,63))
box("进料喉上沿", "items", "frame", (16,45,48,25,48,64))
for z0,z1 in ((48,50),(62,64)):
    box("进料喉侧挡板", "items", "frame", (16,35,z0,25,45,z1))
for x in (32,46):
    box("下模换位导轨", "press", "tool", (x,37,65,x+2,39,79))
box("后侧铸锭模底板", "casting", "tool", (32,36,70,48,39,83))
for x in (32,46):
    box("后侧铸锭模边", "casting", "tool", (x,39,71,x+2,44,83))

# Cylinder head, fastened directly to both overhead beams. The moveable ram is a
# smaller section than the fixed bore and the guard encloses its entire stroke.
box("液压缸底法兰", "press", "tool", (25,89,45,55,96,67))
box("液压缸筒", "press", "cylinder", (29,96,47,51,115,65), CASING)
box("缸盖", "press", "tool", (27,115,45,53,120,67))
box("液压驱动机壳", "drive", "motor", (32,120,48,48,128,64), "create:mechanical_press")
box("活塞杆", "press", "rod", (37,75,53,43,123,59), motion="ram")
box("动压板上座", "press", "tool", (33,72,50,47,76,62), motion="ram")
box("动压板", "press", "tool", (30,69,48,50,72,64), motion="ram")
for z in (43,67):
    for x in (19,57):
        box("防护罩连接座", "guard", "tool", (x,43,z,x+4,84,z+2))
    for y in (43,80):
        box("防护罩横框", "guard", "frame", (23,y,z,57,y+4,z+2))
    for x in (26,33,40,47,54):
        box("防护格条", "guard", "tool", (x,47,z,x+1,80,z+2))
for x in (26,53):
    box("侧向防护板", "guard", "frame", (x,46,45,x+1,80,67))

# Process fluid and pump oil occupy separate routes. Only the process inlet has
# a fluid capability.
box("后置液压站底架", "drive", "frame", (13,20,85,68,26,115))
box("液压油箱底盘", "drive", "foot", (18,26,87,34,30,111))
box("回油储箱", "drive", "cylinder", (20,30,89,32,55,109), "create:fluid_tank")
box("油箱盖与泵座", "drive", "tool", (18,55,87,34,59,111))
box("液压泵", "drive", "motor", (21,59,91,31,68,103), "create:mechanical_pump")
box("加压管竖段", "drive", "pipe", (22,68,92,26,104,96), PIPE)
box("加压管横段", "drive", "pipe", (22,104,65,26,108,96), PIPE)
box("油缸接头", "drive", "tool", (26,102,63,29,110,69))
box("回油管竖段", "drive", "pipe", (28,68,99,32,97,103), PIPE)
box("回油管横段", "drive", "pipe", (28,97,65,32,101,103), PIPE)
for bounds in ((36,36,91,44,38,126), (36,42,91,44,44,126),
               (36,38,91,38,42,126), (42,38,91,44,42,126)):
    box("熔液进料管", "casting", "fluid", bounds, PIPE)
box("熔液接口法兰上", "casting", "tool", (34,44,126,46,46,128), PIPE)
box("熔液接口法兰下", "casting", "tool", (34,34,126,46,36,128), PIPE)
for x in (34,44):
    box("熔液接口法兰侧", "casting", "tool", (x,36,126,x+2,44,128), PIPE)
box("浇注阀箱", "casting", "frame", (34,34,83,46,46,91), CASING)
box("隔热浇口", "casting", "ceramic", (36,35,77,44,43,83), PIPE)

box("供电箱机壳", "drive", "motor", (48,26,91,64,47,112), CASING)
box("线缆竖槽", "drive", "frame", (58,47,97,63,91,102), CASING)
box("线缆横槽", "drive", "frame", (48,91,97,63,96,102), CASING)
box("线缆跨梁", "drive", "frame", (46,91,65,51,96,97), CASING)
box("操作端悬臂", "controls", "frame", (34,19,28,46,25,35))
box("操作端底座", "controls", "foot", (34,17,21,46,31,29))
box("端子支架", "controls", "frame", (33,31,22,47,35,31))
box("操作面板机壳", "controls", "motor", (32,35,17,48,46,28))
box("显示窗", "controls", "screen", (34,37,16,46,44,17), motion="body")
box("带料工件", "items", "work", (32,39,50,48,42,62), motion="workpiece")
box("压制板材", "items", "work", (32,39,50,48,40,62), motion="plate")
box("凝固锭坯", "casting", "work", (34,39,51,46,42,61), motion="ingot")
box("待脱模金属", "casting", "hot", (34,39,51,46,42,61), motion="cast")

# Review placeholders preserve each real native socket's grid position.
box("原生黄铜漏斗", "items", "native_funnel", (3,32,49,16,47,63), motion="native")
box("原生大型连接器", "drive", "native_power", (64,36,99,75,44,109), motion="native")

ROUTES = {
    "items": [[[0,40,56],[17,40,56],[40,40,56],[63,40,56],[80,40,56]]],
    "casting": [[[40,40,128],[40,40,88],[40,40,76],[40,40,57]],
                [[40,40,57],[64,40,57],[80,40,57]]],
    "drive": [[[79,40,104],[61,40,104],[61,93,100],[49,93,100],[49,93,65]],
              [[25,66,96],[25,106,94],[25,106,65],[35,106,65]]],
    "frame": [[[40,98,56],[40,90,38],[8,90,38],[8,13,38],[8,0,38]],
              [[40,98,56],[40,90,74],[72,90,74],[72,13,74],[72,0,74]]],
}
LABELS = [
    ("固料入口", (0,40,56)), ("固料出口", (80,40,56)), ("熔液入口", (40,40,128)),
    ("FE 输入", (77,40,104)), ("操作界面", (40,40,16)),
]


def occupied(bounds):
    return product(*(range(bounds[i]//16, (bounds[i+3]+15)//16) for i in range(3)))


def construction():
    votes = defaultdict(Counter)
    for part in PARTS:
        if part["motion"] != "body":
            continue
        for pos in occupied(part["bounds"]):
            votes[pos][part["block"]] += 1
    blocks = {pos: types.most_common(1)[0][0] for pos, types in votes.items()}
    blocks.update({CORE: "expedition_industry:hydropress", FUNNEL: "create:brass_funnel",
                   CONNECTOR: "createaddition:large_connector", (2,2,7): PIPE,
                   (2,7,3): "create:mechanical_press"})
    for port in PORTS.values():
        assert tuple(port["pos"]) in blocks, port
    cells = []
    for pos, block in sorted(blocks.items(), key=lambda item: (item[0][1],item[0][2],item[0][0])):
        x, y, z = pos
        assert all(0 <= place < limit for place, limit in zip(pos, SIZE))
        state = {}
        if pos == CORE:
            state = {"facing": "north"}
        if pos == FUNNEL:
            state = {"facing": "west", "extracting": "false"}
        if pos == CONNECTOR:
            state = {"facing": "west", "mode": "push"}
        if block == GIRDER:
            for key, neighbors in {"x": ((x-1,y,z),(x+1,y,z)), "z": ((x,y,z-1),(x,y,z+1)),
                                   "top": ((x,y+1,z),), "bottom": ((x,y-1,z),)}.items():
                if any(blocks.get(adjacent) == GIRDER for adjacent in neighbors):
                    state[key] = "true"
        if block == PIPE:
            state = {"north": "true", "south": "true"} if pos == (2,2,7) else {}
        item = {"pos": pos, "block": block}
        if state:
            item["state"] = state
        cells.append(item)
    return {"size": SIZE, "cells": cells, "ports": PORTS}


def validate():
    layout = construction()
    cells = {tuple(cell["pos"]) for cell in layout["cells"]}
    assert (4,2,3) in cells and (2,2,7) in cells
    for p in PARTS:
        assert all(0 <= p["bounds"][i] < p["bounds"][i+3] <= SIZE[i]*16 for i in range(3)), p
    assert 69-STROKE == 40
    assert (0,1,3) not in cells, "the native inlet needs the full belt cell below"
    for label, (x,y,z) in LABELS:
        if label == "操作界面":
            assert z == CORE[2]*16
