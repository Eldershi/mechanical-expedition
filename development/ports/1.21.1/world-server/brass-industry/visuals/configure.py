"""Multiblocked2 display configuration shared by the installed and packaged machines."""

from copy import deepcopy

from nbtlib import Byte, Compound, Int, List, String

MACHINES = {
    "alloy_furnace": "alloy",
    "hydropress": "press",
    "shaft_furnace": "shaft",
    "electrolytic_cell": "cell",
    "trading_station": "trade",
}
NAMESPACE = "expedition_industry"
FACES = ("frontIO", "backIO", "leftIO", "rightIO", "topIO", "bottomIO")


def element(kind="element", *, key=None, css=(), children=(), translate=None):
    data = Compound({"classes": List[String](css)})
    if key:
        data["id"] = String(key)
    if children:
        data["children"] = indexed(children)
    if translate:
        data["text"] = Compound({"translate": String(translate)})
    return Compound({"type": String(kind), "data": data})


def indexed(children):
    return List[Compound]([
        Compound({**child, "index": Int(index)}) for index, child in enumerate(children)
    ])


def label(key, *css):
    return element("label", css=css, translate=f"gui.{NAMESPACE}.{key}")


def group(kind, direction, count, in_jei=False):
    trait = {"input": "import", "output": "export"}[direction] if in_jei else direction
    prefix = "@" if in_jei else "ui:"
    return element(css=("works-slots",), children=[
        element(f"{kind}-slot", key=f"{prefix}{kind}_{trait}_{slot}",
                css=("works-slot", f"works-{kind}-{direction}"))
        for slot in range(count)
    ])


def decorate_bar(bar, css):
    bar = deepcopy(bar)
    bar["data"]["classes"] = List[String]([String(css)])
    return bar


def machine_ui(name, template, fluids):
    title, _, *unused, progress, energy, inventory = template["template"]["children"]
    title = deepcopy(title)
    title["data"]["classes"] = List[String]([String("works-title")])
    title["data"]["text"]["translate"] = String(f"block.{NAMESPACE}.{name}")
    badge = element(css=("works-badge", f"works-{MACHINES[name]}"))
    header = element(css=("works-header",), children=[badge, title])
    sections = []
    for direction in ("input", "output"):
        caption = f"trade_{direction}" if name == "trading_station" else f"item_{direction}"
        children = [label(caption, "works-caption"), group("item", direction, 4)]
        if direction in fluids:
            children.extend([label(f"fluid_{direction}", "works-caption"),
                             group("fluid", direction, 2)])
        sections.append(element(css=("works-column",), children=children))
    process = decorate_bar(progress, "works-process")
    machine_rows = element(css=("works-process-row",), children=[sections[0], process, sections[1]])
    power = element(css=("works-power-row",), children=[
        label("power", "works-caption"), decorate_bar(energy, "works-power"),
    ])
    inventory = deepcopy(inventory)
    inventory["data"]["classes"] = List[String]([String("works-inventory")])
    children = [header, machine_rows, power, label("inventory", "works-caption"), inventory]
    template["template"]["children"] = indexed(children)
    template["template"]["classes"] = List[String]([String("works-panel")])
    template["stylesheets"].append(String(f"{NAMESPACE}:lss/works"))
    template.pop("builtin_styles", None)


def jei_ui(name, template, fluid_in, fluid_out):
    process = element("progress-bar", key="@progress_bar", css=("works-process",))
    items = element(css=("works-process-row",), children=[
        group("item", "input", 4, True), process, group("item", "output", 4, True),
    ])
    rows = [element(css=("works-header",), children=[
        element(css=("works-badge", f"works-{MACHINES[name]}")),
        element("label", css=("works-title",), translate=f"block.{NAMESPACE}.{name}"),
    ]), items]
    if fluid_in or fluid_out:
        rows.append(element(css=("works-jei-fluids",), children=[
            group("fluid", "input", fluid_in, True),
            group("fluid", "output", fluid_out, True),
        ]))
    rows.append(element(css=("works-jei-details",), children=[
        element("progress-bar", key="@forge_energy_import_0", css=("works-jei-power",)),
        element("label", key="@duration", css=("works-caption",)),
        element(key="@condition"),
    ]))
    template["template"]["children"] = indexed(rows)
    template["template"]["classes"] = List[String]([String("works-panel"), String("works-jei")])
    template["stylesheets"].append(String(f"{NAMESPACE}:lss/works"))
    template.pop("builtin_styles", None)
    return template


def configure_visuals(name, definition, fluid_input, fluid_output):
    for trait in definition["machineSettings"]["traitDefinitions"]:
        # The face badges describe installed physical capabilities.
        assert all(trait["capabilityIO"][face] == trait["recipeHandlerIO"] for face in FACES), trait
    root = definition["stateMachine"]["root"]
    for state, visual in (("formed", "ready"), ("working", "working"),
                          ("waiting", "waiting"), ("suspend", "suspend")):
        renderer = Compound({
            "type": String("json_model"),
            "data": Compound({"modelLocation": String(f"{NAMESPACE}:block/works/{name}_{visual}")}),
        })
        if name in {"alloy_furnace", "hydropress", "trading_station"}:
            animation = Compound({
                "type": String("custom_script"),
                "data": Compound({"rendererName": String(f"{NAMESPACE}:{name}_motion")}),
            })
            renderer = Compound({"type": String("renderer_group"),
                                 "data": Compound({"renderers": List[Compound]([renderer, animation])})})
        root["children"].append(Compound({
            "name": String(state),
            "renderer": Compound({"_enable": Byte(1), "value": renderer}),
        }))
    fluids = {direction for direction, enabled in (("input", fluid_input), ("output", fluid_output)) if enabled}
    machine_ui(name, definition["machineSettings"]["uiTemplate"], fluids)
