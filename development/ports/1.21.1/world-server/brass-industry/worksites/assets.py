"""Export editable worksite models, shared-density textures, and a spatial review."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZipFile

from PIL import Image

from hydropress.assets import FACES, PALETTES, atlas, corners, data_uri, texture, visible_faces
from .models import NS, SITES

HERE = Path(__file__).resolve().parent
OVERLAY = HERE.parent/"overlay/kubejs/assets"/NS
MATERIALS = {
    **PALETTES,
    "cast_iron": ("industrial_iron_block.png", (83,78,76)),
    "copper": ("copper_casing.png", (137,87,59)),
    "insulator": ("industrial_iron_block_top.png", (171,169,146)),
    "graphite": ("industrial_iron_block.png", (60,62,62)),
    "window": ("andesite_casing.png", (76,133,129)),
    "glow": ("industrial_iron_block.png", (174,91,58)),
    "vault": ("vault/vault_side_small.png", (103,91,76)),
    "packer": ("packager_horizontal_unpowered.png", (141,104,68)),
    "receive": ("stock_link.png", (67,123,132)),
    "send": ("brass_casing.png", (161,113,52)),
}


def identifier(site, key):
    return str(uuid5(NAMESPACE_URL,f"expedition/{site.name}/{key}"))


def project(site, destination, image, maps, white=False):
    elements, members = [], defaultdict(list)
    if white:
        image=Image.new("RGBA",(16,16),(225,228,225,255))
    for index, part in enumerate(site.parts):
        if part["motion"] not in {"body","native"}:
            continue
        key=identifier(site,f"part/{index}")
        points=corners(part["bounds"])
        center=[(part["bounds"][i]+part["bounds"][i+3])/2 for i in range(3)]
        vertices={f"v{j}":[v[k]-center[k] for k in range(3)] for j,v in enumerate(points)}
        faces={}
        for face_index,f in enumerate(FACES):
            face=[f"v{i}" for i in f]
            uv=[(1,1),(14,1),(14,14),(1,14)] if white else maps[index][face_index]
            faces[f"f{face_index}"]={"vertices":face,"texture":0,"uv":dict(zip(face,uv))}
        elements.append(dict(type="mesh", name=part["name"], uuid=key, origin=center, rotation=[0,0,0],
                             vertices=vertices, faces=faces, visibility=True, export=part["motion"]=="body"))
        members["原生部件定位" if part["motion"]=="native" else "机架" if part["block"]=="create:metal_girder"
                else "机身与接口"].append(key)
    groups=[dict(name=group, origin=[0,0,0], rotation=[0,0,0], uuid=identifier(site,group))
            for group in members]
    data={"meta":{"format_version":"5.0","model_format":"free","box_uv":False},"name":site.label,
          "resolution":{"width":image.width,"height":image.height},"elements":elements,"groups":groups,
          "outliner":[{"uuid":g["uuid"],"isOpen":False,"children":members[g["name"]]} for g in groups],
          "textures":[dict(name=site.label,id="0",uuid=identifier(site,"atlas"),mode="bitmap",
                           width=image.width,height=image.height,uv_width=image.width,
                           uv_height=image.height,source=data_uri(image))]}
    destination.write_text(json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n")


def resources(site, image, surfaces):
    name=site.name+"_assembly"
    out=OVERLAY/"models/block"/name
    textures=OVERLAY/"textures/block"/name
    out.mkdir(parents=True,exist_ok=True)
    textures.mkdir(parents=True,exist_ok=True)
    image.save(textures/"atlas.png",optimize=True)
    atlas_id=f"{NS}:block/{name}/atlas"
    (out/"material.mtl").write_text(f"newmtl worksite\nKd 1 1 1\nmap_Kd {atlas_id}\n")
    vertices=["mtllib material.mtl","o body","usemtl worksite"]
    index=1
    for part,faces in zip(site.parts,surfaces,strict=True):
        if part["motion"]!="body":
            continue
        for _,quad,uv in faces:
            for point in quad:
                relative=[(n-16*cell)/16 for n,cell in zip(point,site.core,strict=True)]
                vertices.append("v "+" ".join(f"{n:.6f}" for n in relative))
            vertices.extend(f"vt {u/image.width:.7f} {1-v/image.height:.7f}" for u,v in uv)
            vertices.append("f "+" ".join(f"{j}/{j}" for j in range(index,index+4)))
            index+=4
    (out/"body.obj").write_text("\n".join(vertices)+"\n")
    settings=dict(loader="neoforge:obj",model=f"{NS}:models/block/{name}/body.obj",flip_v=True,
                  automatic_culling=False,shade_quads=True,textures={"particle":atlas_id})
    (out/"body.json").write_text(json.dumps(settings,indent=2)+"\n")


def build(create, output, preview):
    with ZipFile(create) as archive:
        donor={name:texture(archive,name) for name,_ in MATERIALS.values()}
    scenes={}
    for site in SITES.values():
        image,maps=atlas(donor,site.parts,MATERIALS)
        surfaces=visible_faces(maps,site.parts)
        resources(site,image,surfaces)
        target=output/site.name
        target.mkdir(parents=True,exist_ok=True)
        project(site,target/f"{site.name}-white.bbmodel",image,maps,white=True)
        project(site,target/f"{site.name}.bbmodel",image,maps)
        layout=site.construction()
        (target/"layout.json").write_text(json.dumps(layout,ensure_ascii=False,indent=2)+"\n")
        scenes[site.name]=dict(label=site.label,size=site.size,labels=site.labels,routes=site.routes,
            launches=site.launches,air=layout["air"],cells=[cell["pos"] for cell in layout["cells"]],
            bounds=[16*site.size[0], max(p["bounds"][4] for p in site.parts),16*site.size[2]],
            surfaces=[face for faces in surfaces for face in faces],atlas=data_uri(image),textureSize=image.size)
        print(f"{site.label} {len(layout['cells'])} cells, {image.width}×{image.height} atlas")
    packed=json.dumps(scenes,ensure_ascii=False,separators=(",",":"))
    fragment=(HERE/"review.html.in").read_text().replace("__ASSEMBLY__",packed)
    assert len(fragment.encode()) < 1_000_000
    preview.write_text(fragment)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create",type=Path,required=True)
    parser.add_argument("--design",type=Path,required=True)
    parser.add_argument("--preview",type=Path,required=True)
    args=parser.parse_args()
    build(args.create,args.design,args.preview)
