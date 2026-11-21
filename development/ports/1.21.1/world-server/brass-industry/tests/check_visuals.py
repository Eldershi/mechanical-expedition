"""Verify that the installed art definitions preserve assembly and machine behavior."""

from collections import defaultdict
from copy import deepcopy
from itertools import combinations
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

from nbtlib import load

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import build
from visuals.alloy_furnace import form_shell


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


def check_alloy_shell():
    shell = form_shell()
    planes = defaultdict(list)
    for points, material, uv in (*shell.axis_faces(), *shell.faces):
        assert all(0 <= coordinate <= 16 for pair in uv for coordinate in pair), (material, uv)
        for axis in range(3):
            if not all(p[axis] == points[0][axis] for p in points):
                continue
            span = [tuple(p[d] for p in points) for d in range(3) if d != axis]
            planes[axis, points[0][axis]].append(tuple((min(s), max(s)) for s in span))
    for rectangles in planes.values():
        for a, b in combinations(rectangles, 2):
            assert any(min(high, end) <= max(low, start)
                       for (low, high), (start, end) in zip(a, b)), (a, b)
    for start, end, material in shell.solids:
        assert end[0] <= 0 or start[0] >= 16 or end[2] <= 16 or start[2] >= 32, (material, start, end)
    print("Alloy shell preserves a full-width ladder bay and has no overlapping coplanar rectangles.")


if __name__ == "__main__":
    check_visual_snapshots()
    check_alloy_shell()
