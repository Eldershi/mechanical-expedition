#!/usr/bin/env python3
"""Generate 1.21.1 drop tables for the retained CMI ores."""

import argparse
from copy import deepcopy
import json
from pathlib import Path
from zipfile import ZipFile


ORE_DROPS = {
    "certus_quartz": "ae2:certus_quartz_crystal",
    "etrium": "cmi:raw_etrium",
}


def build_loot(vanilla, pack):
    with ZipFile(vanilla) as jar:
        template = json.loads(jar.read("data/minecraft/loot_table/blocks/deepslate_diamond_ore.json"))
    directory = pack / "data/cmi/loot_table/blocks"
    directory.mkdir(parents=True, exist_ok=True)
    for obsolete in ("quartz_ore", "deepslate_quartz_ore", "peat_block"):
        (directory / f"{obsolete}.json").unlink(missing_ok=True)
    for ore, item in ORE_DROPS.items():
        for prefix in ("", "deepslate_"):
            name = f"{prefix}{ore}_ore"
            table = deepcopy(template)
            silk_touch, normal = table["pools"][0]["entries"][0]["children"]
            silk_touch["name"] = f"cmi:{name}"
            normal["name"] = item
            table["random_sequence"] = f"cmi:blocks/{name}"
            (directory / f"{name}.json").write_text(json.dumps(table, indent=2) + "\n")
    meta = {"pack": {"pack_format": 48, "description": "Expedition CMI ore drops"}}
    (pack / "pack.mcmeta").write_text(json.dumps(meta, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vanilla", type=Path)
    parser.add_argument("pack", type=Path)
    options = parser.parse_args()
    build_loot(options.vanilla, options.pack)
