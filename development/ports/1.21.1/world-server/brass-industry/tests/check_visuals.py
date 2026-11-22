"""Verify that the installed art definitions preserve assembly and machine behavior."""

from copy import deepcopy
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from nbtlib import load

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build
from alloy_furnace import construction


def widgets(data):
    for child in data.get("children", ()):
        yield child
        yield from widgets(child["data"])


def slot_ids(template):
    return {str(widget["data"]["id"]) for widget in widgets(template)
            if widget["type"] in {"item-slot", "fluid-slot"}}


def check_visual_snapshots():
    styled = build.STYLED_MACHINES
    with TemporaryDirectory() as scratch:
        output = Path(scratch) / "visual"
        baseline = Path(scratch) / "default"
        assert build.build(output)
        try:
            build.STYLED_MACHINES = {}
            assert build.build(baseline)
        finally:
            build.STYLED_MACHINES = styled
        for path in sorted(output.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(output)
            expected = baseline / relative
            name = path.stem.removeprefix("expedition_")
            if name not in styled or path.suffix not in {".rt", ".mb"}:
                assert path.read_bytes() == expected.read_bytes(), relative
                if path.name.startswith("expedition_industry_alloy_furnace_"):
                    packaged = HERE / "visuals/predicates" / path.name
                    assert path.read_bytes() == packaged.read_bytes(), packaged
                continue
            base = load(expected, gzipped=False)["data"]
            visual = load(path, gzipped=False)["data"]
            if path.suffix == ".rt":
                assert base["recipe_type"] == visual["recipe_type"], name
                assert slot_ids(base["ui"]["template"]) == slot_ids(visual["ui"]["template"]), name
                published = HERE / "recipe-types" / path.name
            else:
                data = deepcopy(visual)
                current = data["definition"]
                original = base["definition"]
                root = current["stateMachine"]["root"]
                assert [str(child["name"]) for child in root["children"]] == [
                    "formed", "working", "waiting", "suspend",
                ], name
                assert slot_ids(current["machineSettings"]["uiTemplate"]["template"]) == slot_ids(
                    original["machineSettings"]["uiTemplate"]["template"]
                ), name
                root["children"].clear()
                current["machineSettings"]["uiTemplate"] = original["machineSettings"]["uiTemplate"]
                assert data == base, name
                published = HERE / "visuals/multiblock" / path.name
            assert path.read_bytes() == published.read_bytes(), published
    print(f"Visual snapshots preserve assembly, collision, capabilities and slot bindings for {len(styled)} machines.")


def check_alloy_blueprints():
    layout = construction()
    cells = {tuple(cell["pos"]): (cell["block"], cell.get("state", {})) for cell in layout["cells"]}
    source = HERE.parents[1] / "create-blueprints/schematics"
    for family in ("andesite", "brass"):
        file = source / f"Expedition_CMI_alloy_furnace_{family}.nbt"
        blueprint = load(file, gzipped=True)
        states = [{
            "name": str(state["Name"]),
            "props": {key: str(value) for key, value in state.get("Properties", {}).items()},
        } for state in blueprint["palette"]]
        actual = {tuple(cell["pos"]): (states[int(cell["state"])]["name"], states[int(cell["state"])]["props"])
                  for cell in blueprint["blocks"]}
        assert tuple(blueprint["size"]) == (5, 11, 5)
        expected = {pos: (name.replace("create:andesite_funnel", f"create:{family}_funnel"), props)
                    for pos, (name, props) in cells.items()}
        assert len(actual) == 88 and actual == expected, file
    print("Both blueprints match the 88-position alloy furnace pattern.")


if __name__ == "__main__":
    check_visual_snapshots()
    check_alloy_blueprints()
