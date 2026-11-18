#!/usr/bin/env python3
"""Expose Steam Letters' installed bronze sprites to the CMI device models."""

import argparse
import json
from pathlib import Path
from zipfile import ZipFile


TEXTURE_DIRECTORY = "assets/steam_letters/textures/"
DEVICE_DIRECTORY = "block/steam/"
TIERS = ("cast_iron", "steel")


def install_aliases(jar_path, assets):
    sources = []
    with ZipFile(jar_path) as jar:
        for name in sorted(jar.namelist()):
            if not name.startswith(TEXTURE_DIRECTORY + DEVICE_DIRECTORY) or not name.endswith(".png"):
                continue
            path = name.removeprefix(TEXTURE_DIRECTORY).removesuffix(".png")
            if "/bronze/" not in path and "/bronze_" not in path:
                continue
            for tier in TIERS:
                alias = path.replace("/bronze/", f"/{tier}/").replace("/bronze_", f"/{tier}_")
                sources.append({
                    "type": "minecraft:single",
                    "resource": f"steam_letters:{path}",
                    "sprite": f"steam_letters:{alias}",
                })

    if not sources:
        raise ValueError("No Steam Letters device textures found")
    target = assets / "minecraft/atlases/blocks.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    atlas = json.loads(target.read_text()) if target.exists() else {"sources": []}
    aliases = {source["sprite"] for source in sources}
    atlas["sources"] = [source for source in atlas["sources"] if source.get("sprite") not in aliases]
    atlas["sources"].extend(sources)
    target.write_text(json.dumps(atlas, indent=2) + "\n")
    return len(sources)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steam-letters", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    options = parser.parse_args()
    print(f"{install_aliases(options.steam_letters, options.assets)} Steam Letters sprite aliases")
