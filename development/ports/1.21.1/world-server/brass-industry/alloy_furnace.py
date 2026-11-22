"""Generate the formed pattern and physical port routing from the construction layout."""

from collections import defaultdict
from itertools import product
import json
from pathlib import Path

from nbtlib import Byte, Compound, Double, Int, List, String, load

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "alloy-furnace"
MACHINE = "alloy_furnace"
NAMESPACE = "expedition_industry"
FACINGS = {"west": "north", "north": "east", "east": "south", "south": "west"}
FACES = {"north": "frontIO", "east": "rightIO", "south": "backIO", "west": "leftIO",
         "up": "topIO", "down": "bottomIO"}
FACES_LOCAL = {world: FACES[local] for world, local in FACINGS.items()}
CONTROLLER = (1, 1, 2)
CONTROLLER_BLOCK = f"{NAMESPACE}:{MACHINE}"
FUNNEL = "create:andesite_funnel"
CONNECTOR = "createaddition:large_connector"
NATIVE = {FUNNEL, CONNECTOR}


def construction():
    return json.loads((SOURCE / "layout.json").read_text())


def settings_shape(boxes):
    keys = ("minX", "minY", "minZ", "maxX", "maxY", "maxZ")
    return Compound({"_enable": Byte(1), "value": List[Compound](
        Compound({key: Double(n) for key, n in zip(keys, bounds, strict=True)}) for bounds in boxes
    )})


def cell_shapes(source):
    """Split rendered solids at block boundaries, including the attached walk-on deck."""
    cells = {tuple(cell["pos"]): cell["block"] for cell in source["cells"]}
    owned = set(cells)
    boxes = defaultdict(set)
    for bounds in json.loads((SOURCE / "collision.json").read_text()):
        for cell in product(*(range(int(bounds[i] // 16), int(-(-bounds[i + 3] // 16))) for i in range(3))):
            lo = [max(bounds[i], cell[i] * 16) for i in range(3)]
            hi = [min(bounds[i + 3], (cell[i] + 1) * 16) for i in range(3)]
            if cell in owned:
                anchor = cell
            else:
                # A small overhang belongs to an adjacent structural block.
                candidates = [pos for pos in owned if sum(abs(a-b) for a, b in zip(pos, cell)) == 1
                              and cells[pos] not in NATIVE]
                if not candidates:
                    continue
                anchor = min(candidates)
            if cells[anchor] in NATIVE:
                continue
            x, y, z = anchor
            result = (1 + z - hi[2]/16, lo[1]/16-y, lo[0]/16-x,
                      1 + z - lo[2]/16, hi[1]/16-y, hi[0]/16-x)
            if all(result[i] < result[i + 3] for i in range(3)):
                boxes[anchor].add(result)
    return {pos: sorted(parts) for pos, parts in boxes.items()}


def layout_entry(layouts):
    source = construction()
    assert tuple(source["size"]) == (5, 11, 5)
    shapes = cell_shapes(source)
    entries = {tuple(data["pos"]): data for data in source["cells"]}
    assert len(entries) == 88 and entries[CONTROLLER]["block"] == CONTROLLER_BLOCK
    routes = {tuple(data["pos"]): (name, data) for name, data in source["ports"].items()}
    layers = [[[" "] * 5 for _ in range(5)] for _ in range(11)]
    parts, fixtures, config = {}, {}, {}
    for index, (pos, cell) in enumerate(entries.items()):
        x, y, z = pos
        north_x, north_z = 4-z, x
        block = cell["block"]
        props = {key: FACINGS.get(value, value) for key, value in cell.get("state", {}).items()}
        props = {FACINGS.get(key, key): value for key, value in props.items()}
        if block == "create:metal_girder":
            props = {{"x": "z", "z": "x"}.get(key, key): value for key, value in props.items()}
        state = block + ("[" + ",".join(f"{key}={value}" for key, value in props.items()) + "]" if props else "")
        marker = "m" if block == CONTROLLER_BLOCK else chr(0x100 + index)
        layers[y][north_z][north_x] = marker
        if marker == "m":
            continue
        fixtures[f"{north_x},{y},{north_z}"] = state
        choices = [block]
        requirements = {}
        if block == FUNNEL:
            requirements["facing"] = props["facing"]
            choices = [f"create:{family}{inlet}" for family in ("andesite", "brass")
                       for inlet in ("_funnel", "_belt_funnel")]
        elif block == CONNECTOR:
            requirements["facing"] = props["facing"]
        elif block == "create:chute":
            requirements["facing"] = "down"
        if requirements or len(choices) > 1:
            candidates = [candidate + "[" + ",".join(f"{key}={value}" for key, value in requirements.items()) + "]"
                          for candidate in choices]
        else:
            candidates = choices
        parts[marker] = candidates[0]
        config[marker] = (candidates, None if block in NATIVE else shapes.get(pos, []), routes.get(pos))
    layouts[MACHINE] = {"layout": [["".join(row) for row in layer] for layer in layers],
                        "blocks": parts, "fixture_states": fixtures}
    return config, shapes[CONTROLLER]


def proxy_settings(boxes, port):
    channels = []
    if port:
        name, data = port
        enabled = {FACES_LOCAL[face] for face in data["faces"]}
        capability = {"internal": String("NONE"), **{
            face: String(data["io"] if face in enabled else "NONE") for face in FACES.values()
        }}
        channels.append(Compound({"traitNameFilter": String(name), "capabilityIO": Compound(capability)}))
    return Compound({
        "_enable": Byte(1), "enable": Byte(1),
        "stateMachine": Compound({"root": Compound({"name": String("base"), "shape": settings_shape(boxes)})}),
        "proxyCapabilities": Compound({"uid": Int(len(channels)), "payload": List[Compound](channels)}),
    })


def configure_controller(definition, boxes):
    definition["multiblockSettings"]["showUIWhenClickStructure"] = Byte(0)
    for trait in definition["machineSettings"]["traitDefinitions"]:
        for face in trait["capabilityIO"]:
            trait["capabilityIO"][face] = String("NONE")
        if "autoIO" in trait:
            trait["autoIO"]["enable"] = Byte(0)
    block = definition["blockProperties"]
    block["canOcclude"] = Byte(0)
    block["collisionShapeFullBlock"] = Byte(0)
    block["isSuffocating"] = Byte(0)
    root = definition["stateMachine"]["root"]
    for state in root["children"]:
        state["shape"] = settings_shape(boxes)
        state["renderer"]["value"] = Compound({"type": String("custom_script"),
            "data": Compound({"rendererName": String(f"{NAMESPACE}:{MACHINE}_assembly")})})


def apply_pattern(folder, path, config, predicate_for, write):
    project = load(folder / path, gzipped=False)
    holders = project["data"]["placeholders"]["holders"]
    for index, (choices, boxes, port) in enumerate(config.values(), start=2):
        holder = holders[index]
        existing = str(holder["predicates"][0]["path"])
        references = []
        for alternative, choice in enumerate(choices):
            predicate = predicate_for(choice, {})
            if choice.split("[", 1)[0] in (FUNNEL, "create:brass_funnel"):
                predicate["requirements"].append(Compound({"property": String("extracting"), "value": String("false")}))
            if boxes is not None:
                predicate["proxyWhileFormed"] = proxy_settings(boxes, port)
            relative = Path(existing.removesuffix(".predicate.nbt") + (f"_{alternative}" if alternative else "")
                            + ".predicate.nbt")
            write(folder, relative, {"type": String("predicate"), "data": predicate})
            references.append(Compound({"built-in": Byte(0), "path": String(relative.as_posix())}))
        holder["predicates"] = List[Compound](references)
    project.save(folder / path, gzipped=False)
