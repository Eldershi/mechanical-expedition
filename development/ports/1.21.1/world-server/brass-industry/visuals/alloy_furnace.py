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
RETAINED = frozenset(" BMQSUVm")


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
    "beam": CREATE + "girder_pole_side_connected",
    "plate": METAL + "plate_metal/industrial_iron_plate_metal",
    "tank_wall": TANK + "vertical_connected",
    "flange": CREATE + "industrial_iron_block_top",
    "refractory": NS + ":block/works/firebrick",
    "tank": TANK + "vertical",
    "cap": TANK + "top_outer",
    "duct": CREATE + "industrial_iron_block",
    "access": NS + ":block/works/alloy_access",
    "guard": NS + ":block/works/alloy_guard",
    "grille": CREATE + "redstone_requester",
    "throat": CREATE + "blaze_heater_brazier",
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
        low, high = tuple(map(min, zip(a, b))), tuple(map(max, zip(a, b)))
        if material == "beam":
            span = [y-x for x, y in zip(low, high)]
            material = "beam_" + str(span.index(max(span)))
        self.solids.append((low, high, material))

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
        polygon = ((85, 9), (88, 9), (96, 19), (93, 21))
        points = [(x, y, z) for x in (37, 43) for y, z in polygon]
        for indexes in ((0,1,2,3), (7,6,5,4), (4,5,1,0),
                        (5,6,2,1), (6,7,3,2), (7,4,0,3)):
            self.panel(tuple(points[i] for i in reversed(indexes)), "plate", turn)

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
                surface, texture_coords = finish_face(material, axis, sign, points, uv)
                yield tuple(points), surface, texture_coords


def finish_face(material, axis, sign, points, uv):
    if material.startswith("beam_"):
        along = int(material[-1])
        if axis == along:
            return "plate", tuple(uv)
        # Create's connected sprite contains four variants in a 32x32 atlas.
        # Bottom-right is connected at both ends. Its central strip is fully opaque.
        across = 3 - axis - along
        start = min(p[across] for p in points)
        end = max(p[across] for p in points)
        center = (start + end)/2
        width = end-start
        longitudinal = [p[along] for p in points]
        first_tile = min(longitudinal)//16 * 16
        return "beam", tuple(
            (12 + (p[across]-center)*min(1, 8/width)/2, 16-(p[along]-first_tile)/2)
            for p in points
        )
    if material == "tank_wall":
        if axis == 1:
            return "cap", tuple(uv)
        # The airtight tank uses Create's rectangular CT atlas. Preserve every pixel of
        # a 16x16 tile, selecting the connected variant from its neighbours on the shell.
        across = 2 if axis == 0 else 0
        column = min(p[across] for p in points)//16 - 1
        if (axis, sign) in {(0, 1), (2, -1)}:
            column = 2 - column
            uv = [(16-u, v) for u,v in uv]
        height = min(p[1] for p in points)
        row = 0 if height >= 80 else 2 if height < 48 else 1
        return material, tuple((4*(column+1)+u/4, 4*row+v/4) for u,v in uv)
    if material == "access" and (axis != 0 or points[0][0] != 4):
        return "plate", tuple(uv)
    return material, tuple(uv)


def perimeter_ranges(turn):
    # Cut the west deck around the ladder bay alongside the tank.
    return ((9,48), (64,71)) if turn == 3 else ((9,71),)


def guardrails(shell, turn):
    # The ladders have an open bay at the deck edge.
    post_centers = (24, 68) if turn == 3 else (24,56)
    for x in post_centers:
        shell.box((x-2,28,6), (x+2,53,10), "plate", turn)
    if turn == 3:
        shell.box((20,50,6), (46,53,10), "beam", turn)
        shell.box((65,50,6), (71,53,10), "beam", turn)
    else:
        shell.box((20,50,6), (60,53,10), "beam", turn)

    # One continuous punched skirt contains the burner bank.
    apron = 16 if turn == 3 else 13
    shell.box((16,4,apron), (64,6,17), "plate", turn)
    shell.box((16,15,apron), (64,17,17), "plate", turn)
    for x in (16,32,48):
        z = (apron+17)/2
        shell.panel(((x+16,6,z),(x,6,z),(x,15,z),(x+16,15,z)), "guard", turn,
                    ((16,12),(0,12),(0,3),(16,3)))


def form_shell():
    shell = Shell()
    for turn in range(4):
        for x in (24, 56):
            if turn == 3 and x == 56:
                continue
            # Flanged column, actual bearing plate, and a cross-member to the inner ring.
            shell.box((x-5,0,3), (x+5,2,13), "plate", turn)
            shell.box((x-4,2,4), (x+4,14,6), "beam", turn)
            shell.box((x-4,2,10), (x+4,14,12), "beam", turn)
            shell.box((x-1,2,6), (x+1,14,10), "beam", turn)
            shell.box((x-5,14,3), (x+5,17,13), "plate", turn)
            shell.box((x-2,4,11), (x+2,6,16.5), "plate", turn)
            shell.box((x-3,17,9), (x+3,26,24), "beam", turn)
            shell.box((x-5,25,4), (x+5,30,12), "plate", turn)
        for left, right in perimeter_ranges(turn):
            shell.box((left,16,5), (right,29,11), "beam", turn)
        shell.box((8,18,8), (14,25,14), "plate", turn)
        shell.box((34,20,8), (46,29,23), "plate", turn)
        shell.box((36,25,7 if turn else 17), (44,88,14 if turn else 24), "beam", turn)
        shell.box((34,24,6 if turn else 15), (46,29,15 if turn else 24), "plate", turn)
        shell.box((35,46,12), (45,51,21), "plate", turn)
        shell.box((34,84,6), (46,89,19 if turn == 0 else 15), "plate", turn)
        shell.box((34,92,16), (46,96,25), "flange", turn)
        shell.brace(turn)
        guardrails(shell, turn)
    # The service panel and ladder are adjacent. The upper landing has a bearing on the end cap.
    shell.box((34,51,4), (46,64,9), "access", 3)
    shell.box((16,110,16), (32,112,32), "plate")
    shell.box((24,96,21), (30,110,30), "plate")
    shell.ring((16,24,16), (64,30,64), 8, "plate")
    shell.ring((16,17,16), (64,24,64), 3, "refractory")
    shell.ring((16,30,16), (64,32,64), 7, "flange")
    shell.ring((16,32,16), (64,96,64), 4, "tank_wall")
    # The upper casing closes on a single end flange with its own shoulder and service neck.
    shell.ring((16,96,16), (64,98,64), 12, "cap")
    shell.ring((23,98,23), (57,100,57), 10, "cap")
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
    shell.ring((34,151,34), (46,174,46), 2, "duct")
    for turn in range(4):
        # Each grille is one two-sided face. Its narrow edge and slots are part of the texture.
        shell.panel(((48,152,32),(32,152,32),(32,168,32),(48,168,32)), "grille", turn,
                    ((8,7),(0,7),(0,0),(8,0)))
        # The Blaze Burner cage has a short folded rim above its straight wall.
        shell.panel(((46,174,34),(34,174,34),(32,176,32),(48,176,32)), "throat", turn,
                    ((0.5,3.5),(7.5,3.5),(7.5,3),(0.5,3)))
    shell.ring((32,151,32), (48,152,48), 4, "flange")
    shell.ring((32,168,32), (48,170,48), 4, "flange")
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
    if kind == "guard":
        d.rectangle((0,0,15,15), fill="#4c5659")
        for x in (2,6,10,14):
            d.rectangle((x-1,5,x+1,10), fill="#252e33")
            d.rectangle((x-1,6,x,9), fill=(0,0,0,0))
            d.line((x-1,10,x,10), fill="#75807c")
    elif kind == "access":
        d.rectangle((0,0,15,15), fill="#6c7472")
        d.rectangle((2,1,13,11), fill="#4b5551", outline="#929780")
        d.rectangle((4,3,11,7), fill="#27424a", outline="#222e33")
        d.line((5,5,10,5), fill="#80c4bd")
        d.point((5,9), fill="#d2ae66")
        d.line((8,9,10,9), fill="#acb0a0")
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
    # Neutralize the blue cast in the airtight-tank steel while keeping the native atlas.
    tank_steel = dict.fromkeys(("tank_wall", "tank", "cap"), "1.00 0.98 0.87")
    export.files[f"{NS}/{MODELS}/{SHELL}.obj"] = obj(form_shell())
    export.files[f"{NS}/{MODELS}/{SHELL}.mtl"] = "\n".join(
        f"newmtl {name}\nKd {tank_steel.get(name, '1 1 1')}\nmap_Kd {texture}\n"
        for name, texture in TEXTURES.items()
    ).encode()
    export.json(NS, f"{MODELS}/{SHELL}", {
        "loader": "neoforge:obj", "model": f"{NS}:{MODELS}/{SHELL}.obj",
        "automatic_culling": False, "shade_quads": True, "flip_v": False,
        "textures": {"particle": TEXTURES["duct"]},
    })
    for kind in ("case","ports","terminal","guard","access"):
        export.png(NS, f"block/works/alloy_{kind}", panel_image(kind))
