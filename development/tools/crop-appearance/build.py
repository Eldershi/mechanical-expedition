#!/usr/bin/env python3
"""Build client model overrides that use installed Farmer's Delight textures."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


ITEMS = {
    "kaleidoscope_cookery:tomato": "tomato",
    "kaleidoscope_cookery:tomato_seed": "tomato_seeds",
    "kaleidoscope_cookery:rice": "rice",
    "kaleidoscope_cookery:rice_panicle": "rice_panicle",
    "thermal:tomato": "tomato",
    "thermal:tomato_seeds": "tomato_seeds",
    "thermal:rice": "rice",
    "thermal:rice_seeds": "rice",
    "thermal:onion": "onion",
}


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def build(instance, output):
    resources = {}
    for path in sorted((instance / "mods").glob("*.jar")):
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if name.startswith(("assets/farmersdelight/", "assets/thermal/", "assets/kaleidoscope_cookery/", "assets/cofh_core/")) and name.endswith((".json", ".png")):
                    resources[name] = archive.read(name)

    models = {}

    def add_model(namespace, name, value):
        path = f"assets/{namespace}/models/{name}.json"
        if path not in resources:
            raise ValueError(f"Missing installed source model: {path}")
        models[path] = value

    def crop(namespace, name, texture):
        source = json.loads(resources[f"assets/{namespace}/models/block/{name}.json"])
        if not {"parent", "textures"} <= set(source) or set(source) - {"parent", "textures", "render_type"} or len(source["textures"]) != 1:
            raise ValueError(f"Crop model requires review: {namespace}:{name}")
        key = next(iter(source["textures"]))
        source["textures"] = {key: texture if ":" in texture else f"farmersdelight:block/{texture}"}
        add_model(namespace, f"block/{name}", source)

    for item, target in ITEMS.items():
        namespace, name = item.split(":")
        add_model(namespace, f"item/{name}", {"parent": f"farmersdelight:item/{target}"})

    for age in range(8):
        stage = age * 3 // 7
        crop("kaleidoscope_cookery", f"crop/tomato/stage{age}", f"tomatoes_stage{stage}")
        crop("thermal", f"onion_{age}", f"onions_stage{stage}")
        # Thermal rice occupies one block; its final ages show the grain head.
        rice = f"rice_stage{min(3, age * 3 // 5)}" if age < 6 else f"rice_panicles_stage{age - 4}"
        crop("thermal", f"rice_{age}", rice)
        # Cookery reserves three segments, with an invisible top before age 4.
        stalk = "rice_supporting" if age >= 6 else "rice_stage3"
        middle = f"rice_stage{age}" if age < 4 else stalk
        head = f"rice_panicles_stage{age - 4}" if age >= 4 else f"kaleidoscope_cookery:block/crop/rice/stage{age}_up"
        crop("kaleidoscope_cookery", f"crop/rice/stage{age}_down", stalk)
        crop("kaleidoscope_cookery", f"crop/rice/stage{age}_middle", middle)
        crop("kaleidoscope_cookery", f"crop/rice/stage{age}_up", head)

    for age in range(11):
        crop("thermal", f"tomato_{age}", f"tomatoes_stage{age * 3 // 10}")

    # Resolve all inherited models and textures, including indirect texture keys.
    def resolve(identifier, chain=()):
        namespace, name = identifier.split(":")
        path = f"assets/{namespace}/models/{name}.json"
        if path in chain:
            raise ValueError(f"Model cycle: {path}")
        if path not in resources:
            # Minecraft's built-in generated item and block templates are unchanged.
            if namespace == "minecraft":
                return {}
            raise ValueError(f"Missing model: {path}")
        value = models.get(path) or json.loads(resources[path])
        textures = resolve(value["parent"], chain + (path,)) if "parent" in value else {}
        textures.update(value.get("textures", {}))
        return textures

    for path in models:
        namespace, name = path.split("/", 2)[1:]
        textures = resolve(f"{namespace}:{name.removeprefix('models/').removesuffix('.json')}")
        for key, texture in textures.items():
            seen = set()
            while texture.startswith("#"):
                reference = texture[1:]
                if reference in seen or reference not in textures:
                    raise ValueError(f"Invalid texture key: {path}: {key}")
                seen.add(reference)
                texture = textures[reference]
            ns, name = texture.split(":")
            if f"assets/{ns}/textures/{name}.png" not in resources:
                raise ValueError(f"Missing texture: {texture}")

    # All variants of each affected crop must refer to an overridden model.
    variants = 0
    for namespace, block in (("thermal", "tomato"), ("thermal", "onion"), ("thermal", "rice"),
                             ("kaleidoscope_cookery", "tomato_crop"), ("kaleidoscope_cookery", "rice_crop")):
        states = json.loads(resources[f"assets/{namespace}/blockstates/{block}.json"])
        for value in states["variants"].values():
            for variant in value if isinstance(value, list) else [value]:
                ns, name = variant["model"].split(":")
                if f"assets/{ns}/models/{name}.json" not in models:
                    raise ValueError(f"Uncovered crop state: {variant['model']}")
                variants += 1

    hashes = {}
    for path, value in sorted(models.items()):
        destination = output / "kubejs" / path
        if destination.exists() and destination.read_bytes() != encoded(value):
            raise ValueError(f"Refusing to overwrite a different model: {path}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(encoded(value))
        hashes[f"kubejs/{path}"] = hashlib.sha256(encoded(value)).hexdigest()
    return {"itemModels": len(ITEMS), "cropModels": len(models) - len(ITEMS),
            "coveredBlockstateVariants": variants, "files": hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(build(args.instance, args.output), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
