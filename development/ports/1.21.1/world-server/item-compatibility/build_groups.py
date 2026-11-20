#!/usr/bin/env python3
"""Build recipe alternatives from the installed client names and active material tags."""

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import unicodedata


GENERIC_LABELS = {
    "?", "music disc", "ambience disc", "音乐唱片", "环境唱片",
    "锻造模板", "smithing template", "旗帜图案", "banner pattern",
    "advancement icon", "进度图标",
}
COMPATIBLE_MATERIAL = re.compile(
    r"c:(?:dusts|gears|gems|ingots|nuggets|plates|raw_materials|rods|wires|storage_blocks"
    r"|crops|seeds|fruits|vegetables)/[a-z0-9_]+"
)
ISOLATED_TAG_MEMBERS = {
    "powergrid:wire", "powergrid:iron_wire", "powergrid:golden_wire", "powergrid:insulated_copper_wire",
}


def displayed_name(value):
    text = re.sub(r"§[0-9a-fk-or]", "", value, flags=re.IGNORECASE).strip()
    return unicodedata.normalize("NFC", text)


def build(catalog, material_tags):
    defaults = {
        item["id"]: item for item in catalog["items"]
        if item["defaultStack"] and item["id"] != "minecraft:air"
        and not item["id"].startswith("fluidlogistics:fluid_proxy/")
        and ":debug_" not in item["id"]
    }
    groups = defaultdict(set)
    for item in defaults.values():
        for locale in ("chinese", "english"):
            name = displayed_name(item[locale])
            if name and name.lower() not in GENERIC_LABELS and name != item["key"]:
                groups[locale, name].add(item["id"])
    for name, values in material_tags.items():
        if COMPATIBLE_MATERIAL.fullmatch(name):
            groups["material", name].update(set(values) & defaults.keys() - ISOLATED_TAG_MEMBERS)
    groups = sorted({tuple(sorted(values)) for values in groups.values() if len(values) > 1})
    alternatives = defaultdict(set)
    for group in groups:
        for item in group:
            alternatives[item].update(group)
    augmented_tags = {}
    for tag, values in material_tags.items():
        members = set(values)
        additions = set().union(*(alternatives.get(item, ()) for item in members)) - members
        if additions:
            augmented_tags[tag] = sorted(additions)
    return groups, dict(sorted(augmented_tags.items()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("material_tags", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    groups, tags = build(json.loads(args.catalog.read_bytes()), json.loads(args.material_tags.read_bytes()))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = ",\n".join("    " + json.dumps(group, ensure_ascii=False) for group in groups)
    tag_lines = ",\n".join(f"    {json.dumps(tag)}: {json.dumps(additions)}" for tag, additions in tags.items())
    args.output.write_text('{\n  "groups": [\n' + lines + '\n  ],\n'
                           '  "augmentedTags": {\n' + tag_lines + '\n  }\n}\n', encoding="utf-8")
    print(f"{len(groups)} groups, {len(tags)} ingredient tags, {len({item for group in groups for item in group})} item IDs")
