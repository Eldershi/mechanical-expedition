"""Bind the hydraulic press build cells, collision and sided automation."""

from collections import defaultdict

from .model import CONNECTOR, CORE, FUNNEL, PARTS, PORTS, SIZE, construction, occupied, validate
import alloy_furnace

MACHINE = "hydropress"
NATIVE = {FUNNEL, CONNECTOR}


def cell_boxes():
    boxes = defaultdict(set)
    for part in PARTS:
        if part["motion"] != "body":
            continue
        bounds = part["bounds"]
        for cell in occupied(bounds):
            if cell in NATIVE:
                continue
            x, y, z = cell
            base = (x*16, y*16, z*16)
            local = tuple(max(0, bounds[i]-base[i])/16 for i in range(3)) + tuple(
                min(16, bounds[i+3]-base[i])/16 for i in range(3))
            boxes[cell].add(local)
    return {pos: sorted(parts) for pos, parts in boxes.items()}


def layout_entry(layouts):
    validate()
    boxes = cell_boxes()
    routes = {tuple(data["pos"]): (name, data) for name, data in PORTS.items()}
    width, height, depth = SIZE
    layers = [[[" "] * width for _ in range(depth)] for _ in range(height)]
    parts, fixtures, config = {}, {}, {}
    for index, entry in enumerate(construction()["cells"]):
        pos = tuple(entry["pos"])
        x,y,z = pos
        block = entry["block"]
        state = entry.get("state", {})
        marker = "m" if pos == CORE else chr(0x100 + index)
        layers[y][z][x] = marker
        if pos == CORE:
            continue
        fixtures[f"{x},{y},{z}"] = block + ("[" + ",".join(f"{k}={v}" for k,v in state.items()) + "]" if state else "")
        choices = [block]
        if pos == FUNNEL:
            choices = [f"create:brass{variant}[facing=west]" for variant in ("_funnel","_belt_funnel")]
        elif pos == CONNECTOR:
            choices = [f"{block}[facing=west]"]
        parts[marker] = choices[0]
        config[marker] = (choices, None if pos in NATIVE else boxes[pos], routes.get(pos))
    layouts[MACHINE] = {"layout": [["".join(row) for row in layer] for layer in layers],
                        "blocks": parts, "fixture_states": fixtures}
    return config, boxes[CORE]


def configure_controller(definition, boxes):
    alloy_furnace.configure_controller(definition, boxes, MACHINE)


def apply_pattern(folder, path, config, predicate_for, write):
    alloy_furnace.apply_pattern(folder, path, config, predicate_for, write, alloy_furnace.FACES)
