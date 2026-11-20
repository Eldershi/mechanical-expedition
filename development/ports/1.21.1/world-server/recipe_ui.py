"""Build the JEI template for Multiblocked2 recipe types."""

from nbtlib import Compound, Int, List, String


def recipe_ui(items=4, fluid_in=0, fluid_out=0):
    def widget(kind, identifier=None, classes=(), children=()):
        data = Compound()
        if identifier:
            data["id"] = String(identifier)
        if classes:
            data["classes"] = List[String](classes)
        if children:
            data["children"] = indexed(children)
        return Compound({"type": String(kind), "data": data})

    def indexed(children):
        return List[Compound](
            Compound({**child, "index": Int(index)}) for index, child in enumerate(children)
        )

    def slots(kind, direction, count):
        return widget("element", classes=("recipe-row",), children=[
            widget(kind + "-slot", f"@{kind}_{direction}_{index}")
            for index in range(count)
        ])

    row = [slots("item", "import", items), widget("progress-bar", "@progress_bar", ("recipe-arrow",)),
           slots("item", "export", items)]
    children = [widget("element", classes=("recipe-row",), children=row)]
    if fluid_in or fluid_out:
        children.append(widget("element", classes=("recipe-row",), children=[
            slots("fluid", "import", fluid_in),
            slots("fluid", "export", fluid_out),
        ]))
    children.append(widget("element", classes=("recipe-row",), children=[
        widget("progress-bar", "@forge_energy_import_0", ("recipe-power",)),
        widget("label", "@duration"),
        widget("element", "@condition"),
    ]))
    return Compound({
        "stylesheets": List[String](["ldlib2:lss/mc"]),
        "template": Compound({
            "children": indexed(children),
            "classes": List[String](["panel_bg", "recipe-panel"]),
        }),
        "builtin_styles": String(
            ".recipe-panel { width: 176; padding-all: 4; gap-all: 4; } "
            ".recipe-row { flex-direction: row; align-items: center; justify-content: space-between; } "
            ".recipe-arrow { width: 14; height: 10; } .recipe-power { width: 78; height: 10; }"
        ),
    })
