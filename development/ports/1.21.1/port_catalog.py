#!/usr/bin/env python3
"""Convert the Expedition storage catalog to the Create 6.0.10 component schema."""

import argparse
import json
from pathlib import Path
import re
import shutil


OLD_FILTER = re.compile(
    r'give @s create:attribute_filter\{display:\{Name:("(?:\\.|[^"\\])*")\},'
    r'WhitelistMode:0,MatchedAttributes:\[\{attributeId:"create:in_tag",'
    r'tag:"(expedition:catalog/[a-z_]+)",Inverted:0b\}\]\} 1'
)


def convert(source, target):
    source_base = source / "data/expedition"
    old_tags = source_base / "tags/items/catalog"
    old_function = source_base / "functions/catalog/give_filters.mcfunction"
    tags = sorted(path for path in old_tags.glob("*.json") if re.fullmatch(r"[a-z_]+\.json", path.name))
    target_tags = {f"expedition:catalog/{path.stem}" for path in tags}
    converted = []
    seen = set()
    for line in old_function.read_text().splitlines():
        if not line.strip():
            continue
        match = OLD_FILTER.fullmatch(line)
        if not match:
            raise ValueError(f"Unsupported catalog filter: {line}")
        name, tag = json.loads(match[1]), match[2]
        if tag not in target_tags or tag in seen:
            raise ValueError(f"Unknown or duplicated catalog tag: {tag}")
        seen.add(tag)
        attributes = [{"attribute": {"type": "create:in_tag", "value": tag}, "inverted": False}]
        converted.append(
            "give @s create:attribute_filter["
            f"minecraft:custom_name={json.dumps(name, ensure_ascii=False)},"
            'create:attribute_filter_whitelist_mode="whitelist_disj",'
            f"create:attribute_filter_matched_attributes={json.dumps(attributes, separators=(',', ':'))}] 1"
        )
    if seen != target_tags or not seen:
        raise ValueError("Catalog functions and tag files must describe the same categories")

    out = target / "data/expedition"
    tag_output = out / "tags/item/catalog"
    function_output = out / "function/catalog"
    tag_output.mkdir(parents=True, exist_ok=True)
    function_output.mkdir(parents=True, exist_ok=True)
    for path in tags:
        shutil.copyfile(path, tag_output / path.name)
    (function_output / "give_filters.mcfunction").write_text("\n".join(converted) + "\n")
    meta = json.loads((source / "pack.mcmeta").read_text())
    meta["pack"]["pack_format"] = 48
    (target / "pack.mcmeta").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n")
    print(f"Converted {len(converted)} filters and {len(tags)} item tags")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    convert(args.source, args.target)
