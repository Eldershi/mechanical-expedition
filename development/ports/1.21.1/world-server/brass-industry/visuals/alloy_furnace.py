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
RETAINED = frozenset(" BMm")


def render_mask(structures):
    structures = Path(structures)
    data = json.loads(structures.read_text())["alloy_furnace"]
    alternatives = json.loads(structures.with_name("structure-alternatives.json").read_text())
    lines = []
    for y, layer in enumerate(data["layout"]):
        for z, row in enumerate(layer):
            for x, marker in enumerate(row):
                if marker not in RETAINED:
                    predicate = data["blocks"][marker]
                    block = alternatives.get(predicate, [predicate])[0].split("[",1)[0]
                    lines.append(f"{x-2} {y-8} {z-2} {block}")
    return ("\n".join(lines) + "\n").encode()

TEXTURES = {
    "beam": NS + ":block/works/alloy_girder",
    "rail": METAL + "catwalks/industrial_iron_catwalk_rail",
    "deck": METAL + "sheet_metal/industrial_iron_sheet_metal",
    "rim": NS + ":block/works/alloy_exhaust_rim",
    "keys": NS + ":block/works/alloy_keys",
    "winding": METAL + "sheet_metal/copper_sheet_metal",
    "ceramic": CREATE + "andesite_block",
    "plate": METAL + "plate_metal/industrial_iron_plate_metal",
    "tank_wall": TANK + "vertical_connected",
    "flange": CREATE + "industrial_iron_block_top",
    "refractory": NS + ":block/works/firebrick",
    "tank": TANK + "vertical",
    "cap": TANK + "top_outer",
    "duct": CREATE + "industrial_iron_block",
    "access": NS + ":block/works/alloy_access",
    "guard": NS + ":block/works/alloy_guard",
    "grille": NS + ":block/works/alloy_grille",
    "throat": NS + ":block/works/alloy_exhaust_fold",
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
        elif material == "rail":
            material = "rail_" + str(1 if high[1]-low[1] > 3 else 0 if high[0]-low[0] >= high[2]-low[2] else 2)
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
        polygon = ((68, 10), (71, 10), (78, 19), (75, 21))
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
        across = 3 - axis - along
        low = min(p[across] for p in points)
        width = max(p[across] for p in points) - low
        first_tile = min(p[along] for p in points)//16 * 16
        return "beam", tuple((2+12*(p[across]-low)/width, 16-(p[along]-first_tile)) for p in points)
    if material.startswith("rail_"):
        along = int(material[-1])
        if axis == along:
            return "rail", tuple((3+u/8,2+v/8) for u,v in uv)
        across = 3-axis-along
        start = min(p[across] for p in points)
        width = max(p[across] for p in points) - start
        local = min(p[along] for p in points)//16*16
        if along == 1:
            return "rail", tuple((3+(p[across]-start)*2/width, 16-(p[along]-local)*12/16) for p in points)
        return "rail", tuple((p[along]-local, 2+2*(p[across]-start)/width) for p in points)
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
    if material == "keys" and (axis != 1 or sign < 0):
        return "deck", tuple(uv)
    if material == "rim":
        return material, tuple((4+u/2, 5+v/4) for u,v in uv)
    return material, tuple(uv)


def guardrail(shell, turn):
    # Create Deco's industrial catwalk rail has a flat top rail and narrow stanchions.
    shell.box((10,48,10), (70,50,12), "rail", turn)
    for x in (22, 38, 56):
        shell.box((x,30,10), (x+2,48,12), "rail", turn)


def service_terminal(shell):
    turn = 3
    # A sloped CRT face sits behind the bezel, above a separate level keyboard shelf.
    shell.box((32,49,3), (48,52,13), "keys", turn)
    shell.box((35,52,3.75), (45,54.25,8), "flange", turn)
    x0, x1, y0, y1 = 34, 46, 54, 64

    def point(x, y, inset=0):
        return (x, y, 2 + (y-y0)*1.75/(y1-y0) + inset)

    def front(lo, hi, bot, top, material, inset=0, uv=None):
        shell.panel((point(hi,bot,inset), point(lo,bot,inset),
                     point(lo,top,inset), point(hi,top,inset)), material, turn, uv)

    front(x0,x1,y0,56,"deck")
    front(x0,x1,62,y1,"deck")
    front(x0,35,56,62,"deck")
    front(45,x1,56,62,"deck")
    front(35,45,56,62,"access",0.75,((13,11),(3,11),(3,4),(13,4)))
    for x in (35,45):
        shell.panel((point(x,56),point(x,56,0.75),point(x,62,0.75),point(x,62)),"deck",turn)
    for y in (56,62):
        shell.panel((point(35,y),point(45,y),point(45,y,0.75),point(35,y,0.75)),"deck",turn)
    for x in (x0,x1):
        shell.panel((point(x,y0),(x,y0,4.75),(x,y1,4.75),point(x,y1)),"deck",turn)
    for y in (y0,y1):
        shell.panel((point(x0,y),(x0,y,4.75),(x1,y,4.75),point(x1,y)),"flange",turn)
    shell.panel(((x0,y0,4.75),(x1,y0,4.75),(x1,y1,4.75),(x0,y1,4.75)),"deck",turn)


def induction_coil(shell):
    for y in (81,87,93):
        shell.box((13,y,13),(67,y+2,15),"winding")
        for x in (13,65):
            shell.box((x,y,15),(x+2,y+2,67),"winding")
        shell.box((15,y,65),(37,y+2,67),"winding")
        shell.box((43,y,65),(65,y+2,67),"winding")
    # The joins turn up at the rear and the two ends run back to the socket.
    shell.box((35,81,65),(37,89,67),"winding")
    shell.box((43,87,65),(45,95,67),"winding")
    for x, low in ((43,81),(35,93)):
        shell.box((x,low,66),(x+2,low+2,70),"winding")
        shell.box((x,low,68),(x+2,106,70),"winding")
        shell.box((x,104,48),(x+2,106,68),"winding")
        shell.box((x,104,48),(x+2,122,50),"winding")
    for turn in range(4):
        for x in (25,55):
            shell.box((x,82,14),(x+2,94,17),"ceramic",turn)


def form_shell():
    shell = Shell()
    for turn in range(4):
        for x in (24, 56):
            # The column feet carry the continuous deck frame.
            shell.box((x-5,0,3), (x+5,2,13), "flange", turn)
            shell.box((x-4,2,4), (x+4,16,12), "beam", turn)
            shell.box((x-5,14,3), (x+5,18,13), "flange", turn)
            shell.box((x-2,4,11), (x+2,7,18), "plate", turn)
            shell.box((x-3,18,8), (x+3,27,21), "beam", turn)
        shell.box((10,18,5), (70,26,13), "beam", turn)
        shell.box((10,26,5), (70,30,16), "deck", turn)

        # I-section column with wide flanges and a recessed web.
        shell.box((34,30,5), (46,72,8), "beam", turn)
        shell.box((34,30,13), (46,72,16), "beam", turn)
        shell.box((38,30,8), (42,72,13), "beam", turn)
        shell.box((33,27,4), (47,32,17), "flange", turn)
        shell.box((33,68,4), (47,73,17), "flange", turn)
        shell.box((34,75,16), (46,79,23), "flange", turn)
        shell.brace(turn)
        guardrail(shell, turn)
    service_terminal(shell)
    shell.ring((16,26,16), (64,32,64), 9, "deck")

    # The lower rim, perforated guard and lower ash pan close the burner enclosure.
    shell.ring((16,4,16), (64,7,64), 2, "flange")
    shell.ring((16,17,16), (64,26,64), 3, "refractory")
    for turn in range(4):
        for x in (16,32,48):
            shell.panel(((x+16,7,16.5),(x,7,16.5),(x,17,16.5),(x+16,17,16.5)),
                        "guard", turn, ((16,13),(0,13),(0,3),(16,3)))
    shell.box((17,1,17), (63,3,63), "deck")
    for turn in range(4):
        shell.box((16,3,23),(24,7,26),"flange",turn)
    shell.ring((16,32,16), (64,96,64), 4, "tank_wall")
    # The upper casing closes on a single end flange with its own shoulder and service neck.
    shell.ring((16,96,16), (64,99,64), 9, "cap")
    shell.ring((24,99,24), (56,103,56), 9, "flange")
    shell.ring((27,103,27), (53,112,53), 3, "tank")
    shell.ring((26,112,26), (54,114,54), 7, "cap")
    shell.box((32,114,32),(48,124,35),"tank")
    shell.box((32,114,35),(35,124,48),"tank")
    shell.box((45,114,35),(48,124,48),"tank")
    # The lower controller face is accessible through this rear opening.
    shell.box((32,114,47),(36,124,50),"ceramic")
    shell.box((44,114,47),(48,124,50),"ceramic")
    induction_coil(shell)
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
                    ((16,16),(0,16),(0,0),(16,0)))
        # The Blaze Burner cage has a short folded rim above its straight wall.
        shell.panel(((46,174,34),(34,174,34),(32,175,32),(48,175,32)), "throat", turn,
                    ((14,10),(2,10),(0,6),(16,6)))
        shell.panel(((36,174,36),(44,174,36),(46,175,34),(34,175,34)), "throat", turn,
                    ((4,12),(12,12),(14,10),(2,10)))
    shell.ring((32,151,32), (48,152,48), 4, "flange")
    shell.ring((32,168,32), (48,170,48), 4, "flange")
    shell.ring((32,175,32), (48,176,48), 2, "rim")
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
    if kind == "girder":
        d.rectangle((0,0,15,15), fill="#4d5354")
        d.rectangle((3,0,12,15), fill="#555b5b")
        d.line((2,0,2,15), fill="#787b76")
        d.line((13,0,13,15), fill="#303637")
        for y in (4,12):
            for x in (3,11):
                d.point((x,y), fill="#9a9a8d")
                d.point((x,y+1), fill="#373e3f")
    elif kind == "grille":
        d.rectangle((0,0,15,15), fill="#656d6c", outline="#8c9290")
        for y in range(2,14):
            for x in range(2,14):
                if (x//2+y//2)%2 == 0:
                    d.point((x,y), fill=(0,0,0,0))
                elif x%2==0 or y%2==0:
                    d.point((x,y), fill="#8a8d83")
        for x,y in ((1,1),(14,1),(1,14),(14,14)):
            d.point((x,y), fill="#b5b5a7")
    elif kind == "exhaust_rim":
        d.rectangle((0,0,15,15),fill="#828988")
        d.rectangle((0,0,15,5),fill="#a3aaa5")
        d.rectangle((0,9,15,15),fill="#596261")
        d.line((0,8,15,8),fill="#a8ada4")
        for x in (4,11):
            d.point((x,7),fill="#c2c4b9")
            d.point((x,9),fill="#414a4a")
    elif kind == "exhaust_fold":
        d.rectangle((0,0,15,15),fill="#526060")
        d.rectangle((0,6,15,7),fill="#a4aca6")
        d.rectangle((0,8,15,9),fill="#7c8682")
        d.line((0,10,15,10),fill="#3a4346")
        for x in (3,12):
            d.point((x,9),fill="#adb1a5")
    elif kind == "keys":
        d.rectangle((0,0,15,15),fill="#707771")
        d.rectangle((1,3,14,12),fill="#424b4a")
        for x in (3,5,7,9,11):
            for y in (4,7,10):
                d.point((x,y),fill="#a1a6a0")
        d.line((6,11,10,11),fill="#b5b8ac")
    elif kind == "guard":
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
    tilt = {"origin": [8,9,8], "axis": "x", "angle": 22.5}
    def frame(lo, hi, faces):
        return elt(lo, hi, faces, rotation=tilt)
    side = "#case"
    return {"parent": "minecraft:block/block",
            "textures": {
                "particle": f"{NS}:block/works/alloy_case", "case": f"{NS}:block/works/alloy_case",
                "keys": f"{NS}:block/works/alloy_keys", "ports": f"{NS}:block/works/alloy_ports",
                "screen": f"{NS}:block/works/alloy_base"},
            "elements": [
                elt([0,0,0],[16,3,16],{"down":"#ports","up":"#keys","north":side,"south":"#ports","west":side,"east":side}),
                elt([4,3,9],[12,6,14],{"west":side,"east":side,"north":side,"south":side}),
                frame([1,5,5],[15,13,13],{"west":side,"east":side,"up":side,"down":side,"south":"#ports"}),
                frame([1,5,4],[15,6,5],{"north":side,"west":side,"east":side,"down":side}),
                frame([1,12,4],[15,13,5],{"north":side,"west":side,"east":side,"up":side}),
                frame([1,6,4],[3,12,5],{"north":side,"west":side,"east":side}),
                frame([13,6,4],[15,12,5],{"north":side,"west":side,"east":side}),
                frame([3,6,4],[13,6,5],{"up":side}),
                frame([3,12,4],[13,12,5],{"down":side}),
                elt([3,6,5],[13,12,5],{"north":"#screen"},rotation=tilt,uv={"north":[3,2,13,8]}),
            ]}


def add_gui_art(export):
    from PIL import Image, ImageDraw

    def texture(name, size, fill):
        image = Image.new("RGBA", size, fill)
        w,h = size
        draw = ImageDraw.Draw(image)
        return image, draw, w,h

    def save(name,image):
        export.png(NS,f"gui/works/alloy_{name}",image)

    def bevel(draw, box, light, dark, fill):
        x0,y0,x1,y1 = box
        draw.rectangle(box,fill=fill)
        draw.line((x0,y1,x0,y0,x1,y0),fill=light)
        draw.line((x0+1,y1,x1,y1,x1,y0+1),fill=dark)

    image,d,w,h = texture("case", (218,198), "#3f4748")
    bevel(d,(1,1,w-2,h-2),"#a6ada6","#2e3637","#707977")
    bevel(d,(4,4,w-5,h-5),"#7b8381","#4c5554","#646d6d")
    for x,y in ((4,4),(w-5,4),(4,h-5),(w-5,h-5)):
        d.point((x,y),fill="#c4c6ba")
    save("case",image)

    image,d,w,h = texture("screen", (202,105), "#3e4947")
    bevel(d,(1,1,w-2,h-2),"#303a3c","#adb2a7","#555f5c")
    bevel(d,(4,4,w-5,h-5),"#182222","#708078","#253433")
    d.line((7,7,w-8,7),fill="#3e514c")
    d.line((7,h-8,w-8,h-8),fill="#344745")
    save("screen",image)

    for name, stripe in (("item_input","#79a797"),("fluid_input","#6facad"),
                         ("item_output","#b4ac81"),("fluid_output","#aa9767")):
        image,d,w,h = texture(name,(18,18),"#273636")
        bevel(d,(0,0,w-1,h-1),"#445451","#7b8580","#192827")
        d.line((3,15,14,15),fill=stripe)
        save(name,image)

    for name, fill in (("process_empty","#374a44"),("process_fill","#83baa2")):
        image,d,_,_ = texture(name,(26,13),(0,0,0,0))
        d.polygon(((1,4),(17,4),(17,1),(24,6),(17,11),(17,8),(1,8)),fill=fill)
        save(name,image)

    for name, fill in (("energy_empty","#142321"),("energy_fill","#659c85")):
        image,d,w,h = texture(name,(126,12),"#374840")
        bevel(d,(0,0,w-1,h-1),"#253534","#66746c",fill)
        if name.endswith("fill"):
            for x in range(6,125,8):
                d.line((x,2,x,9),fill="#547f70")
        save(name,image)


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
    add_gui_art(export)
    for kind in ("case","ports","guard","access","girder","keys","grille","exhaust_rim","exhaust_fold"):
        export.png(NS, f"block/works/alloy_{kind}", panel_image(kind))
