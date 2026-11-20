#!/usr/bin/env python3
"""Install the smeltery and foundry resource pack and NeoForge recipes."""

import argparse
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
PACK_NAME = "Create-Style-Seared-NeoForge-1.21.1.zip"


def mod_jar(instance, pattern):
    jars = sorted((instance / "mods").glob(pattern))
    if len(jars) != 1:
        raise ValueError(f"Expected one {pattern} in {instance / 'mods'}")
    return jars[0]


def install(client=None, server=None):
    instances = {instance.resolve() for instance in (client, server) if instance is not None}
    for instance in instances:
        mod_jar(instance, "TinkersConstruct-Unofficial-Port-1.21.1-*-NeoForge.jar")
        mod_jar(instance, "create-1.21.1-*.jar")

    if client is not None:
        from build_resourcepacks import build_texture_set, write_pack

        paxi = client / "config/paxi"
        packs = paxi / "resourcepacks"
        packs.mkdir(parents=True, exist_ok=True)
        foundry_jar = mod_jar(client, "TinkersConstruct-Unofficial-Port-1.21.1-*-NeoForge.jar")
        create_jar = mod_jar(client, "create-1.21.1-*.jar")
        with ZipFile(foundry_jar) as foundry, ZipFile(create_jar) as create:
            textures = build_texture_set(foundry, create, "modernfoundry")
            write_pack(packs / PACK_NAME, foundry, "modernfoundry", 34, textures)

        order_path = paxi / "resourcepack_load_order.json"
        order = json.loads(order_path.read_text(encoding="utf-8")) if order_path.is_file() else {}
        order["loadOrder"] = [pack for pack in order.get("loadOrder", []) if pack != PACK_NAME] + [PACK_NAME]
        order_path.write_text(json.dumps(order, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    for instance in instances:
        shutil.copytree(HERE / "kubejs", instance / "kubejs", dirs_exist_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path)
    parser.add_argument("--server", type=Path)
    args = parser.parse_args()
    if not (args.client or args.server):
        parser.error("provide a prepared --client, --server, or both")
    install(args.client, args.server)
