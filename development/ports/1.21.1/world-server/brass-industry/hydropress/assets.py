"""Bake 1:1 pixel faces for the hydraulic press and export editable Blockbench meshes."""

import argparse
from base64 import b64encode
from collections import defaultdict
from io import BytesIO
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

from PIL import Image, ImageDraw
from .model import CORE, LABELS, PARTS, ROUTES, SIZE, STROKE, construction, validate

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent / "overlay/kubejs/assets/expedition_industry"
ROOT = "expedition_industry"
MODEL = "hydropress_assembly"
PIXELS = 1024
FACES = ((0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0))
NORMALS = ((1,-1),(1,1),(2,-1),(0,1),(2,1),(0,-1))
PALETTES = {
    "girder": ("girder_pole_side_connected.png", (89,87,80)),
    "frame": ("industrial_iron_block.png", (76,79,80)),
    "foot": ("industrial_iron_block_top.png", (86,85,79)),
    "tool": ("mechanical_press_head.png", (120,124,120)),
    "rod": ("mechanical_press_pole.png", (157,161,153)),
    "roller": ("mechanical_press_pole.png", (101,103,98)),
    "cylinder": ("andesite_casing.png", (100,108,101)),
    "motor": ("gearbox.png", (88,100,98)),
    "fluid": ("industrial_iron_block.png", (119,111,105)),
    "pipe": ("mechanical_press_pole.png", (91,100,93)),
    "ceramic": ("industrial_iron_block_top.png", (96,80,69)),
    "native_funnel": ("brass_casing.png", (160,120,62)),
    "native_power": ("andesite_casing.png", (171,148,108)),
    "work": ("industrial_iron_block_top.png", (166,169,158)),
    "hot": ("industrial_iron_block.png", (204,104,49)),
    "screen": ("industrial_iron_block.png", (27,49,44)),
}


def offset(color, amount):
    return tuple(max(0,min(255,value+amount)) for value in color)


def texture(archive, name):
    return Image.open(BytesIO(archive.read(f"assets/create/textures/block/{name}"))).convert("RGBA")


def paint(w, h, material, x_axis, donor, palette=PALETTES):
    source_name, base = palette[material]
    source = donor[source_name]
    tones = [[sum(source.getpixel((x,y))[:3])//3 for x in range(source.width)] for y in range(source.height)]
    mid = sum(map(sum,tones))//(source.width*source.height)
    image = Image.new("RGBA",(w,h))
    pixels = image.load()
    for y in range(h):
        for x in range(w):
            # The donor contributes small variations only inside the material face.
            variation = (tones[(y+4)%source.height][(x+4)%source.width]-mid)//5
            t = (x+.5)/w if x_axis else (y+.5)/h
            if material in {"rod","pipe","fluid","roller"}:
                variation += round(20 - 43*abs(2*t-1))
            pixels[x,y] = (*offset(base,variation),255)
    d = ImageDraw.Draw(image)
    if min(w,h) >= 4 and material not in {"rod","pipe","fluid","roller","screen","work","hot"}:
        d.line((0,0,w-1,0),fill=offset(base,19))
        d.line((0,1,0,h-1),fill=offset(base,8))
        d.line((0,h-1,w-1,h-1),fill=offset(base,-20))
        d.line((w-1,1,w-1,h-1),fill=offset(base,-16))
    if min(w,h) >= 7 and material in {"girder","frame","foot","motor","cylinder","tool"}:
        along_x = w >= h
        length, width = (w,h) if along_x else (h,w)
        for t in sorted({2,length-3,*range(13,length-9,12)}):
            for across in (2,width-3):
                x,y = (t,across) if along_x else (across,t)
                d.point((x,y),fill=offset(base,31))
                d.point((x,y+1),fill=offset(base,-22))
    if material == "motor" and min(w,h) >= 12:
        for y in range(h//2-2,h//2+3,2):
            d.line((w//2-3,y,w//2+3,y),fill=offset(base,-20))
            d.point((w//2+4,y),fill=offset(base,10))
    if material in {"send","receive"} and w>=13 and h>=4:
        mid=w//2
        tip=1 if material=="send" else h-2
        tail=h-2 if material=="send" else 1
        mark=offset(base,70)
        d.line((mid,tip,mid,tail),fill=mark)
        d.line((mid,tip,mid-2,(tip+tail)//2),fill=mark)
        d.line((mid,tip,mid+2,(tip+tail)//2),fill=mark)
    if material == "screen" and w >= 7 and h >= 5:
        d.rectangle((1,1,w-2,h-2),outline=(63,89,78))
        d.line((3,3,w-4,3),fill=(133,174,133))
        d.line((3,4,w-6,4),fill=(85,128,103))
        d.point((w-4,4),fill=(180,183,101))
    return image


def corners(bounds):
    x,y,z,X,Y,Z = bounds
    return [(x,y,z),(X,y,z),(X,y,Z),(x,y,Z),(x,Y,z),(X,Y,z),(X,Y,Z),(x,Y,Z)]


def length(a,b):
    return sum(abs(i-j) for i,j in zip(a,b))


def atlas(donor, parts=PARTS, palette=PALETTES):
    image = Image.new("RGBA",(PIXELS,PIXELS))
    x = y = 1
    row = 0
    tiles = {}
    faces = []
    for part in parts:
        vertices = corners(part["bounds"])
        bounds = part["bounds"]
        maps = []
        for face in FACES:
            a,b,c,d = [vertices[i] for i in face]
            # Put the texture's top edge toward world +Y on walls.
            horizontal = a[1] == b[1]
            w,h = (length(a,b),length(a,d)) if horizontal else (length(a,d),length(a,b))
            material = part["material"]
            key = (material,w,h,(w < h) if material == "roller" else True)
            if key not in tiles:
                if x+w+1 >= PIXELS:
                    x,y,row = 1,y+row+2,0
                assert y+h+1 < PIXELS, "Hydraulic press atlas overflow"
                image.paste(paint(w,h,material,key[3],donor,palette),(x,y))
                # Duplicate edge texels into a one-pixel gutter for the game atlas.
                for crop, point in (((x,y,x+w,y+1),(x,y-1)),((x,y+h-1,x+w,y+h),(x,y+h)),
                                    ((x,y-1,x+1,y+h+1),(x-1,y-1)),
                                    ((x+w-1,y-1,x+w,y+h+1),(x+w,y-1))):
                    image.paste(image.crop(crop),point)
                tiles[key] = (x,y)
                x += w+2
                row = max(row,h)
            u,v = tiles[key]
            uv = [(u,v+h),(u+w,v+h),(u+w,v),(u,v)] if horizontal else [
                (u,v+h),(u,v),(u+w,v),(u+w,v+h)]
            maps.append(uv)
        faces.append(maps)
    # Keep a power-of-two height while avoiding unused atlas rows.
    height = 1 << (y+row+1).bit_length()
    return image.crop((0,0,PIXELS,height)), faces


def subtract_rectangle(rectangle, mask):
    x,y,X,Y = rectangle
    a,b,A,B = max(x,mask[0]),max(y,mask[1]),min(X,mask[2]),min(Y,mask[3])
    if a >= A or b >= B:
        return [rectangle]
    strips = ((x,y,a,Y),(A,y,X,Y),(a,y,A,b),(a,B,A,Y))
    return [rect for rect in strips if rect[0]<rect[2] and rect[1]<rect[3]]


def visible_faces(maps, parts=PARTS):
    """Keep only exposed surfaces, with unique ownership of coplanar pixels."""
    static = [(i,part["bounds"]) for i,part in enumerate(parts) if part["motion"]=="body"]
    surfaces = []
    for index,part in enumerate(parts):
        vertices = corners(part["bounds"])
        exposed=[]
        for face_no, (ids,(axis,sign)) in enumerate(zip(FACES,NORMALS)):
            origin,endpoint,_,opposite = (vertices[i] for i in ids)
            plane = origin[axis]
            a = next(j for j in range(3) if origin[j]!=endpoint[j])
            b = next(j for j in range(3) if origin[j]!=opposite[j])
            wa,hb = endpoint[a]-origin[a],opposite[b]-origin[b]
            w,h = abs(wa),abs(hb)
            sa,sb = wa//w,hb//h
            rectangles=[(0,0,w,h)]
            if part["motion"]=="body":
                for other,bounds in static:
                    if index==other:
                        continue
                    low,high = bounds[axis],bounds[axis+3]
                    covers = low<=plane<high if sign>0 else low<plane<=high
                    earlier = other<index and plane==(high if sign>0 else low)
                    if not covers and not earlier:
                        continue
                    x,X=sorted((bounds[a+k]-origin[a])*sa for k in (0,3))
                    y,Y=sorted((bounds[b+k]-origin[b])*sb for k in (0,3))
                    rectangles = [piece for rect in rectangles for piece in subtract_rectangle(rect,(x,y,X,Y))]
                    if not rectangles:
                        break
            uv0,uv1,_,uv3 = maps[index][face_no]
            for x,y,X,Y in rectangles:
                quad, uv = [], []
                for u,v in ((x,y),(X,y),(X,Y),(x,Y)):
                    point=list(origin)
                    point[a]+=sa*u
                    point[b]+=sb*v
                    quad.append(tuple(point))
                    uv.append(tuple(uv0[j]+(uv1[j]-uv0[j])*u//w+(uv3[j]-uv0[j])*v//h for j in range(2)))
                exposed.append((face_no,quad,uv))
        surfaces.append(exposed)
    return surfaces


def data_uri(image):
    out = BytesIO()
    image.save(out,format="PNG",optimize=True)
    return "data:image/png;base64,"+b64encode(out.getvalue()).decode()


def uid(key):
    return str(uuid5(NAMESPACE_URL,"expedition/hydraulic-press/"+key))


def write_project(path, image, maps, white=False):
    if white:
        image = Image.new("RGBA",(16,16),(225,228,227,255))
    elements, groups = [], defaultdict(list)
    for i, part in enumerate(PARTS):
        if part["motion"] in {"workpiece","plate","cast","ingot","native"}:
            continue
        vertices = corners(part["bounds"])
        center = tuple((a+b)/2 for a,b in zip(part["bounds"],part["bounds"][3:]))
        vert = {f"v{j}":[a-b for a,b in zip(point,center)] for j,point in enumerate(vertices)}
        faces = {}
        for j, ids in enumerate(FACES):
            keys = [f"v{k}" for k in ids]
            uv = [(1,1),(1,15),(15,15),(15,1)] if white else maps[i][j]
            faces[f"f{j}"] = dict(vertices=keys,texture=0,uv=dict(zip(keys,uv)))
        key = uid(f"part/{i}")
        elements.append(dict(type="mesh",name=part["name"],uuid=key,origin=center,rotation=[0,0,0],
                             vertices=vert,faces=faces,visibility=True,export=True))
        groups["ram" if part["motion"]=="ram" else part["group"]].append(key)
    names = {"frame":"机架与承重","press":"液压缸与模台","ram":"活动压头","items":"固料通道",
             "casting":"浇注与铸锭","drive":"液压站与供电","controls":"操作台","guard":"防护罩"}
    definition = [dict(name=names[k],origin=[0,0,0],rotation=[0,0,0],uuid=uid(k),
                       visibility=True,export=True) for k in groups]
    data = dict(meta=dict(format_version="5.0",model_format="free",box_uv=False),name="液压机",
                resolution=dict(width=image.width,height=image.height),elements=elements,groups=definition,
                outliner=[dict(uuid=g["uuid"],isOpen=False,children=groups[k]) for g,k in zip(definition,groups)],
                textures=[dict(name="白模" if white else "液压机材质",id="0",uuid=uid("paint"),
                               mode="bitmap",width=image.width,height=image.height,
                               uv_width=image.width,uv_height=image.height,source=data_uri(image))])
    path.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n")


def write_assets(image, surfaces):
    geometry = OVERLAY / "models/block" / MODEL
    texture_path = OVERLAY / "textures/block" / MODEL / "atlas.png"
    geometry.mkdir(parents=True, exist_ok=True)
    texture_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(texture_path,optimize=True)
    atlas_id = f"{ROOT}:block/{MODEL}/atlas"
    (geometry/"material.mtl").write_text(f"newmtl press\nKd 1 1 1\nmap_Kd {atlas_id}\n")
    for state in ("body","ram","workpiece","plate","cast","ingot"):
        lines = ["mtllib material.mtl",f"o {state}","usemtl press"]
        v = uv_index = 1
        for i,part in enumerate(PARTS):
            if part["motion"] != state:
                continue
            for _,quad,uv in surfaces[i]:
                for point in quad:
                    xyz = [(n-cell*16)/16 for n,cell in zip(point,CORE)]
                    lines.append("v "+" ".join(f"{n:.6f}" for n in xyz))
                lines.extend(f"vt {x/image.width:.7f} {1-y/image.height:.7f}" for x,y in uv)
                lines.append("f "+" ".join(f"{v+j}/{uv_index+j}" for j in range(4)))
                v += 4
                uv_index += 4
        (geometry/f"{state}.obj").write_text("\n".join(lines)+"\n")
        data = dict(loader="neoforge:obj",model=f"{ROOT}:models/block/{MODEL}/{state}.obj",
                    flip_v=True,automatic_culling=False,shade_quads=True,textures={"particle":atlas_id})
        (geometry/f"{state}.json").write_text(json.dumps(data,indent=2)+"\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create",type=Path,required=True)
    parser.add_argument("--design",type=Path,required=True)
    parser.add_argument("--preview",type=Path,required=True)
    args = parser.parse_args()
    validate()
    with ZipFile(args.create) as archive:
        donor = {source:texture(archive,source) for source,_ in PALETTES.values()}
    image,maps = atlas(donor)
    surfaces = visible_faces(maps)
    write_assets(image,surfaces)
    args.design.mkdir(parents=True,exist_ok=True)
    write_project(args.design/"hydraulic-press-white.bbmodel",image,maps,white=True)
    write_project(args.design/"hydraulic-press.bbmodel",image,maps)
    layout = construction()
    (args.design/"layout.json").write_text(json.dumps(layout,indent=2)+"\n")
    scene = dict(parts=[{**{k:p[k] for k in ("group","bounds","motion")},"uv":uv,"surface":faces}
                        for p,uv,faces in zip(PARTS,maps,surfaces)],
                 cells=[cell["pos"] for cell in layout["cells"]],routes=ROUTES,labels=LABELS,size=SIZE,
                 atlas=data_uri(image),textureSize=image.size,stroke=STROKE)
    template = (HERE/"review.html.in").read_text()
    fragment = template.replace("__ASSEMBLY__",json.dumps(scene,ensure_ascii=False,separators=(",",":")))
    assert len(fragment.encode()) < 1_000_000
    args.preview.write_text(fragment)
    print(f"{len(PARTS)} parts; {len(layout['cells'])} construction cells; {image.width}×{image.height} atlas")


if __name__ == "__main__":
    main()
