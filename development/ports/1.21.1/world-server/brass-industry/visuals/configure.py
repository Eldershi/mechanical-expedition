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


def trade_offer(name, rate):
    return element(css=("trade-offer",), children=[
        label(name, "trade-name"),
        label(rate, "trade-rate"),
    ])


def trade_tabs():
    pages = {
        "sell": [
            trade_offer("trade_copper", "trade_credit_2"),
            trade_offer("trade_brass", "trade_credit_4"),
        ],
        "buy": [
            trade_offer("trade_tin", "trade_cost_paper"),
            trade_offer("trade_coolant", "trade_cost_bottle"),
        ],
        "contracts": [label("trade_contracts_unavailable", "trade-note")],
        "delivery": [
            label("trade_delivery_pickup", "trade-note"),
            label("trade_delivery_unavailable", "trade-note"),
        ],
    }
    tabs = []
    panels = []
    for page, widgets in pages.items():
        tab = element("tab", key=f"trade-{page}", css=("trade-tab",))
        tab["data"]["internal"] = List[Compound]([label(f"trade_tab_{page}")["data"]])
        tabs.append(tab)
        panels.append(element(css=("trade-page",), children=widgets))

    # TabView restores its native content and header. The header's scroller
    # nests the external Tab children in its scrollable internal container.
    headers = Compound({"children": indexed(tabs)})
    for _ in range(5):
        headers = Compound({"internal": List[Compound]([headers])})
    result = element("tab-view", key="trade-desk", css=("trade-desk",))
    result["data"].update({
        "internal": List[Compound]([Compound({"children": indexed(panels)}), headers]),
        "tabs": List[Compound]([
            Compound({"tab": Int(index), "content": Int(index)}) for index in range(len(tabs))
        ]),
        "selected": Int(0),
    })
    return result


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
    face = [header, machine_rows, power]
    classes = ["works-panel"]
    inventory_caption = label("inventory", "works-caption")
    if name in {"hydropress", "shaft_furnace", "electrolytic_cell", "trading_station"}:
        classes.append("press-panel")
    if name == "trading_station":
        face.insert(1, trade_tabs())
    if name == "alloy_furnace":
        face = [element(css=("alloy-display",), children=face)]
        classes.append("alloy-panel")
        inventory_caption["data"]["classes"].append(String("alloy-inventory-caption"))
    template["template"]["children"] = indexed([*face, inventory_caption, inventory])
    template["template"]["classes"] = List[String](map(String, classes))
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
    classes = ["works-panel", "works-jei"]
    if name == "alloy_furnace":
        classes.append("alloy-jei")
    if name in {"hydropress", "shaft_furnace", "electrolytic_cell", "trading_station"}:
        classes.append("press-jei")
    template["template"]["classes"] = List[String](map(String, classes))
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
        if name == "alloy_furnace":
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
