"""Use each site's occupied cells for the MBD2 pattern and its sided ports."""

from collections import defaultdict

from .models import SITES, TRADE, occupied
import alloy_furnace

AIR = ["minecraft:air", "minecraft:cave_air", "minecraft:void_air"]


def collision(site):
    boxes = defaultdict(set)
    for part in site.parts:
        if part["motion"] != "body":
            continue
        bounds = part["bounds"]
        for cell in occupied(bounds):
            if cell in site.live:
                continue
            base = tuple(n*16 for n in cell)
            lo = tuple(max(0,bounds[i]-base[i])/16 for i in range(3))
            hi = tuple(min(16,bounds[i+3]-base[i])/16 for i in range(3))
            boxes[cell].add(lo+hi)
    return {pos: sorted(parts) for pos,parts in boxes.items()}


def state_string(cell):
    state = cell["state"]
    return cell["block"] + ("[" + ",".join(f"{key}={v}" for key,v in state.items()) + "]" if state else "")


def layout_entry(site, layouts):
    boxes = collision(site)
    width,height,depth = site.size
    slabs = [[[" "] * width for _ in range(depth)] for _ in range(height)]
    parts, fixtures, config = {}, {}, {}
    for index,cell in enumerate(site.construction()["cells"]):
        pos=tuple(cell["pos"])
        x,y,z=pos
        if pos==site.core:
            slabs[y][z][x]="m"
            continue
        marker=chr(0x100+index)
        slabs[y][z][x]=marker
        block=cell["block"]
        choices=site.live.get(pos,{}).get("choices") or site.replacements.get(block,[block])
        if pos in site.live and block in {"minecraft:hopper","create:packager","create:item_vault","create:stock_link"}:
            choices=[state_string(cell)]
        fixtures[f"{x},{y},{z}"]=state_string(cell)
        parts[marker]=choices[0]
        port=site.ports.get(pos)
        config[marker]=(choices,None if pos in site.live else boxes[pos],port[:2] if port else None)
    if site.name==TRADE:
        for x,y,z in sorted(site.required_empty):
            slabs[y][z][x]="."
        parts["."]=AIR[0]
        config["."]=(AIR,None,None)
    layouts[site.name]={"layout":[["".join(row) for row in band] for band in slabs],
                        "blocks":parts,"fixture_states":fixtures}
    return config,boxes[site.core]


def prepare(layouts):
    return {key:layout_entry(site,layouts) for key,site in SITES.items()}


def configure_controller(name, definition, boxes):
    alloy_furnace.configure_controller(definition,boxes,name)


def apply_pattern(folder, path, config, predicate_for, write):
    alloy_furnace.apply_pattern(folder,path,config,predicate_for,write,alloy_furnace.FACES)
