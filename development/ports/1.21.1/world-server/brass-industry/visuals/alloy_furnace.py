"""Build the formed alloy furnace shell and its one-block control console."""

from collections import defaultdict
import json
from pathlib import Path
from itertools import product
from math import dist, sqrt

NS = "expedition_industry"
CREATE = "create:block/"
TANK = "createcraftedbeginning:block/airtight_tank/"
METAL = "createdeco:block/palettes/"
MODELS = "models/block/works"
SHELL = "alloy_furnace_shell"
RETAINED = frozenset(" BEJMm")


def render_mask(structures):
    data = json.loads(Path(structures).read_text())["alloy_furnace"]
    lines = []
    for y, layer in enumerate(data["layout"]):
        for z, row in enumerate(layer):
            for x, marker in enumerate(row):
                if marker not in RETAINED:
                    block = data["blocks"][marker].split("[", 1)[0]
                    lines.append(f"{x-2} {y-8} {z-2} {block}")
    return ("\n".join(lines) + "\n").encode()

TEXTURES = {
    "beam": CREATE + "girder_pole_side",
    "plate": METAL + "plate_metal/industrial_iron_plate_metal",
    "copper": METAL + "sheet_metal/copper_sheet_metal",
    "heat": NS + ":block/works/alloy_oven_sheet",
    "flange": CREATE + "industrial_iron_block_top",
    "refractory": NS + ":block/works/firebrick",
    "tank": TANK + "vertical",
    "cap": TANK + "top",
    "duct": CREATE + "industrial_iron_block",
    "lamp": NS + ":block/works/andesite_floodlight",
    "grille": NS + ":block/works/alloy_grille",
    "throat": NS + ":block/works/alloy_flue",
}


def radial(point, turn):
    x, y, z = point
    return ((x, y, z), (80-z, y, x), (80-x, y, 80-z), (z, y, 80-x))[turn]


class Shell:
    def __init__(self):
        self.solids = []
        self.faces = []

    def box(self, low, high, material, turn=0):
        a, b = radial(low, turn), radial(high, turn)
        self.solids.append((tuple(map(min, zip(a, b))), tuple(map(max, zip(a, b))), material))

    def ring(self, low, high, wall, material):
        x, y, z = low
        a, b, c = high
        self.box((x, y, z), (a, b, z+wall), material)
        self.box((x, y, c-wall), (a, b, c), material)
        self.box((x, y, z+wall), (x+wall, b, c-wall), material)
        self.box((a-wall, y, z+wall), (a, b, c-wall), material)

    def panel(self, points, material, turn=0, uv=None):
        if uv is None:
            width = min(16, dist(points[0], points[1]))
            height = min(16, dist(points[0], points[-1]))
            uv = ((0, height), (width, height), (width, 0), (0, 0))
        self.faces.append((tuple(radial(p, turn) for p in points), material, uv))

    def brace(self, turn):
        # Diagonal enters both node plates, leaving the other faces free.
        polygon = ((86, 8), (89, 6), (102, 20), (99, 23))
        points = [(x, y, z) for x in (38, 42) for y, z in polygon]
        for indexes in ((0,1,2,3), (7,6,5,4), (4,5,1,0),
                        (5,6,2,1), (6,7,3,2), (7,4,0,3)):
            self.panel(tuple(points[i] for i in reversed(indexes)), "beam", turn)

    def axis_faces(self):
        """Extract only the boundary of the union and weld all internal seams."""
        limits = [sorted({*range(0, size+1, 16), *(p[d] for box in self.solids for p in box[:2])})
                  for d, size in enumerate((80, 176, 80))]
        indexes = [{n: i for i, n in enumerate(axis)} for axis in limits]
        filled = {}
        for low, high, material in self.solids:
            for pos in product(*(range(ids[a], ids[b]) for ids, a, b in zip(indexes, low, high))):
                filled[pos] = material
        planes = defaultdict(set)
        for cell, material in filled.items():
            for axis, sign in product(range(3), (-1, 1)):
                neighbor = list(cell)
                neighbor[axis] += sign
                if tuple(neighbor) in filled:
                    continue
                u, v = (axis+1)%3, (axis+2)%3
                i, j = cell[u], cell[v]
                tile_u, tile_v = limits[u][i]//16, limits[v][j]//16
                planes[(axis, sign, cell[axis]+(sign == 1), material, tile_u, tile_v)].add((i, j))
        for (axis, sign, plane, material, tile_u, tile_v), cells in sorted(planes.items()):
            u, v = (axis+1)%3, (axis+2)%3
            while cells:
                i, j = min(cells)
                end_i = i+1
                while (end_i,j) in cells:
                    end_i += 1
                end_j = j+1
                while all((x,end_j) in cells for x in range(i,end_i)):
                    end_j += 1
                cells.difference_update(product(range(i,end_i),range(j,end_j)))
                uv_corners = [(i,j), (end_i,j), (end_i,end_j), (i,end_j)]
                if sign < 0:
                    uv_corners.reverse()
                points, uv = [], []
                for a, b in uv_corners:
                    p = [0,0,0]
                    p[axis], p[u], p[v] = limits[axis][plane], limits[u][a], limits[v][b]
                    points.append(tuple(p))
                    raw_u = p[u] - tile_u*16
                    raw_v = p[v] - tile_v*16
                    if u == 1:
                        uv.append((raw_v, 16-raw_u))
                    else:
                        uv.append((raw_u, 16-raw_v))
                yield tuple(points), material, tuple(uv)


def form_shell():
    shell = Shell()
    for turn in range(4):
        for x in (24, 56):
            # Flanged column, actual bearing plate, and a cross-member to the inner ring.
            shell.box((x-5,0,3), (x+5,2,13), "plate", turn)
            shell.box((x-4,2,4), (x+4,14,6), "beam", turn)
            shell.box((x-4,2,10), (x+4,14,12), "beam", turn)
            shell.box((x-1,2,6), (x+1,14,10), "beam", turn)
            shell.box((x-5,14,3), (x+5,17,13), "plate", turn)
            shell.box((x-3,17,9), (x+3,26,24), "beam", turn)
            shell.box((x-7,24,3), (x+7,32,13), "plate", turn)
        shell.box((10,16,6), (70,26,10), "beam", turn)
        for y in (16,24):
            shell.box((9,y,4), (71,y+2,12), "beam", turn)
        shell.box((8,18,8), (14,25,14), "plate", turn)
        shell.box((34,20,8), (46,30,23), "plate", turn)
        # Side column starts at the footing, and ties into the hot shell twice.
        if turn == 0:
            # The north column forks around the original lever. Its plate ends at the lever mount.
            shell.box((30,25,7), (35,85,14), "beam")
            shell.box((45,25,7), (50,85,14), "beam")
            shell.box((33,51,16), (47,63,20), "plate")
            for x in (31, 45):
                shell.box((x,51,13), (x+4,63,17), "plate")
            shell.box((29,24,6), (51,28,15), "plate")
            shell.box((29,83,6), (51,85,15), "plate")
        else:
            shell.box((36,25,7), (44,88,14), "beam", turn)
            shell.box((34,24,6), (46,28,15), "plate", turn)
        shell.box((35,46,12), (45,51,21), "plate", turn)
        shell.box((34,83,6), (46,89,16), "plate", turn)
        shell.box((34,98,18), (46,103,29), "plate", turn)
        shell.brace(turn)
    shell.ring((15,24,15), (65,30,65), 8, "plate")
    shell.ring((16,17,16), (64,24,64), 3, "refractory")
    shell.ring((16,30,16), (64,34,64), 7, "flange")
    shell.ring((19,34,19), (61,92,61), 4, "heat")
    shell.ring((18,60,18), (62,63,62), 5, "copper")
    shell.ring((16,92,16), (64,96,64), 8, "flange")
    shell.ring((21,96,21), (59,100,59), 12, "flange")
    # The original upward lights have a low housing on the upper bearing ring.
    for turn in range(4):
        shell.box((17,93,17), (31,97,31), "plate", turn)
        shell.box((19,97,19), (29,100,29), "duct", turn)
        for lo, hi in (((19,19),(29,20)), ((19,28),(29,29)), ((19,20),(20,28)), ((28,20),(29,28))):
            shell.box((lo[0],100,lo[1]), (hi[0],101,hi[1]), "duct", turn)
        x, z = 20, 20
        shell.panel(((x,100.5,z),(x,100.5,z+8),(x+8,100.5,z+8),(x+8,100.5,z)),
                    "lamp", turn, ((4,4),(4,12),(12,12),(12,4)))
    shell.ring((26,100,26), (54,104,54), 5, "cap")
    shell.ring((28,104,28), (52,112,52), 3, "tank")
    shell.ring((27,112,27), (53,114,53), 5, "cap")
    shell.ring((32,114,32), (48,124,48), 3, "tank")
    shell.ring((31,124,31), (49,128,49), 4, "cap")
    shell.ring((44,94,44), (50,112,50), 1, "duct")
    shell.ring((44,112,44), (48,128,48), 1, "duct")
    # Rear fitting mates with the control housing and returns to the exhaust manifold.
    shell.ring((46,128,46), (50,145,50), 1, "duct")
    shell.ring((32,144,32), (50,149,50), 2, "duct")
    shell.ring((32,149,32), (50,151,50), 4, "flange")
    shell.ring((35,151,35), (45,170,45), 2, "duct")
    for turn in range(4):
        shell.box((37,148,26), (43,151,34), "plate", turn)
        shell.box((28,150,28), (30,168,30), "plate", turn)
        # The gaps are transparent pixels on a sheet in front of the actual duct.
        shell.panel(((50,151,29),(30,151,29),(30,167,29),(50,167,29)), "grille", turn,
                    ((0,16),(16,16),(16,0),(0,0)))
        # One flared, open sheet on each side of the exhaust mouth.
        shell.panel(((32,176,32),(48,176,32),(45,170,35),(35,170,35)), "throat", turn,
                    ((0,9),(16,9),(13,16),(3,16)))
    shell.ring((27,149,27), (53,151,53), 3, "plate")
    shell.ring((27,167,27), (53,169,53), 3, "plate")
    return shell


def obj(shell):
    # Coordinates are relative to the north-facing controller, in Minecraft blocks.
    lines = [f"mtllib {SHELL}.mtl", "o AlloyFurnace"]
    vertices, uvs, normals, surfaces = {}, {}, {}, defaultdict(list)
    found = set()
    for points, material, uv in (*shell.axis_faces(), *shell.faces):
        assert all(0 <= c <= limit for p in points for c, limit in zip(p, (80,176,80))), points
        signature = tuple(sorted(points))
        assert signature not in found, points
        found.add(signature)
        a = [b-x for x,b in zip(points[0], points[1])]
        b = [b-x for x,b in zip(points[0], points[2])]
        n = tuple(a[(i+1)%3]*b[(i+2)%3]-a[(i+2)%3]*b[(i+1)%3] for i in range(3))
        length = sqrt(sum(v*v for v in n))
        normal = normals.setdefault(tuple(round(v/length,6) for v in n), len(normals)+1)
        surfaces[material].append("f " + " ".join(
            f"{vertices.setdefault(p, len(vertices)+1)}/{uvs.setdefault(t, len(uvs)+1)}/{normal}"
            for p,t in zip(points,uv,strict=True)))
    for x,y,z in vertices:
        lines.append(f"v {(x-32)/16:g} {(y-128)/16:g} {(z-32)/16:g}")
    lines.extend(f"vt {u/16:g} {v/16:g}" for u,v in uvs)
    lines.extend(f"vn {x:g} {y:g} {z:g}" for x,y,z in normals)
    for material, faces in sorted(surfaces.items()):
        lines.extend([f"usemtl {material}", *faces])
    return ("\n".join(lines) + "\n").encode()


def panel_image(kind):
    from PIL import Image, ImageDraw

    picture = Image.new("RGBA", (16,16))
    d = ImageDraw.Draw(picture)
    if kind == "grille":
        for x in (0, 4, 8, 12, 15):
            d.line((x,0,x,15), fill="#34404a")
            if x < 15:
                d.line((x+1,0,x+1,15), fill="#828989")
        for y in (0, 15):
            d.line((0,y,15,y), fill="#515959")
    elif kind == "flue":
        d.rectangle((0,0,15,15), fill="#505558")
        d.rectangle((0,9,15,10), fill="#999087")
        d.line((2,14,13,14), fill="#646767")
        d.line((3,15,12,15), fill="#373a3c")
    elif kind == "oven_sheet":
        d.rectangle((0,0,15,15), fill="#555e61")
        d.line((2,0,2,15), fill="#60686b")
        d.line((3,0,3,15), fill="#5a6366")
        d.line((12,0,12,15), fill="#4c5559")
        d.line((13,0,13,15), fill="#495257")
    elif kind == "case":
        d.rectangle((0,0,15,15), fill="#6c7472")
        d.line((0,0,15,0), fill="#a4a99a")
        d.line((0,15,15,15), fill="#454e50")
        d.line((1,4,1,12), fill="#868d83")
        for x in (2,13):
            d.point((x,2), fill="#c7ba96")
            d.point((x,13), fill="#3b4344")
    elif kind == "ports":
        picture = panel_image("case")
        d = ImageDraw.Draw(picture)
        d.rectangle((2,6,13,11), fill="#39464a")
        d.rectangle((3,8,4,9), outline="#b9c9c3")
        d.line((6,10,7,7), fill="#dfb36b")
        for x, lamp in ((9,"#69b9b2"),(12,"#dfb36b")):
            d.point((x,8), fill=lamp)
            d.point((x,9), fill="#97634c")
    elif kind == "terminal":
        d.rectangle((0,0,15,15), fill="#333b3c")
        d.rectangle((0,0,15,2), fill="#b5ac90")
        d.rectangle((0,3,15,7), fill="#887e68")
        d.rectangle((0,8,15,14), fill="#9c947c")
        d.line((0,15,15,15), fill="#555b50")
        for x in (1,14):
            d.point((x,4), fill="#dad0a7")
        d.line((6,10,8,10), fill="#deb56e")
        d.rectangle((1,10,3,12), outline="#d4d7c8")
        for x, lamp in ((10,"#69b9b2"),(13,"#dfb36b")):
            d.rectangle((x,10,x+2,12), fill="#554236")
            d.point((x+1,11), fill=lamp)
    return picture


def console_screen(state, frame=None):
    from PIL import Image, ImageDraw

    img = Image.new("RGBA", (16,16), "#131d20")
    d = ImageDraw.Draw(img)
    d.rectangle((3,2,12,7), fill="#233238")
    d.line((3,2,12,2), fill="#4b6566")
    d.line((3,7,12,7), fill="#384b4e")
    if frame is not None:
        d.line((4,6,11,6), fill="#a36b41")
        for x in range(4,12):
            height = 1 + ((x*3 + frame + (x//2)*frame) % 4)
            d.line((x,6-height,x,6), fill="#e1904d" if height > 2 else "#c07242")
            if height > 2:
                d.point((x,6-height), fill="#f4bf76")
    else:
        d.line((4,6,8,6), fill="#4b6664")
    d.point((11,6), fill={"base":"#926853","ready":"#8cc687","working":"#a8cc80",
                          "waiting":"#f6bd67","suspend":"#827d6c"}[state])
    return img


def console_model(elt):
    faces = ("down","up","north","south","west","east")
    def outside(lo, hi, omit):
        return elt(lo, hi, {face: ("#terminal" if face == "north" else "#case")
                            for face in faces if face not in omit})
    return {"parent": "minecraft:block/block",
            "textures": {
                "particle": f"{NS}:block/works/alloy_case", "case": f"{NS}:block/works/alloy_case",
                "terminal": f"{NS}:block/works/alloy_terminal",
                "ports": f"{NS}:block/works/alloy_ports", "screen": f"{NS}:block/works/alloy_base"},
            "elements": [
                # One pixel recess. The four bezel pieces only expose their outer and reveal faces.
                elt([0,0,1],[16,16,16],{"west":"#ports","east":"#ports","south":"#ports",
                                        "up":"#ports","down":"#ports"}),
                outside([0,0,0],[16,8,1], {"south","up"}),
                outside([0,14,0],[16,16,1], {"south","down"}),
                outside([0,8,0],[3,14,1], {"south","up","down"}),
                outside([13,8,0],[16,14,1], {"south","up","down"}),
                elt([3,8,0],[13,8,1],{"up":"#case"}),
                elt([3,14,0],[13,14,1],{"down":"#case"}),
                elt([3,8,0],[3,14,1],{"east":"#case"}),
                elt([13,8,0],[13,14,1],{"west":"#case"}),
                elt([3,8,1],[13,14,1],{"north":"#screen"},uv={"north":[3,2,13,8]}),
            ]}


def add_shell(export):
    export.files[f"{NS}/{MODELS}/{SHELL}.obj"] = obj(form_shell())
    export.files[f"{NS}/{MODELS}/{SHELL}.mtl"] = "\n".join(
        f"newmtl {name}\nKd 1 1 1\nmap_Kd {texture}\n" for name,texture in TEXTURES.items()
    ).encode()
    export.json(NS, f"{MODELS}/{SHELL}", {
        "loader": "neoforge:obj", "model": f"{NS}:{MODELS}/{SHELL}.obj",
        "automatic_culling": False, "shade_quads": True, "flip_v": True,
        "textures": {"particle": TEXTURES["heat"]},
    })
    for kind in ("case","ports","terminal","grille","flue","oven_sheet"):
        export.png(NS, f"block/works/alloy_{kind}", panel_image(kind))
