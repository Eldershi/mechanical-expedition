#!/usr/bin/env python3
"""Install the smeltery and foundry resource pack and NeoForge recipes."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from urllib.request import urlopen

HERE = Path(__file__).resolve().parent
INTEGRATION = HERE.parents[4] / "integrations/resourcepacks/create-style-foundry.json"
OLD_PACK = "Create-Style-Seared-NeoForge-1.21.1.zip"


def mod_jar(instance, pattern):
    jars = sorted((instance / "mods").glob(pattern))
    if len(jars) != 1:
        raise ValueError(f"Expected one {pattern} in {instance / 'mods'}")
    return jars[0]


def install_resource_pack(client, artifact=None):
    resource, = json.loads(INTEGRATION.read_text(encoding="utf-8"))["clientFiles"]
    target = client / resource["path"]
    order_path = target.parent.parent / "resourcepack_load_order.json"
    order = json.loads(order_path.read_text(encoding="utf-8")) if order_path.is_file() else {}

    def matches(data):
        return len(data) == resource["bytes"] and hashlib.sha256(data).hexdigest() == resource["sha256"]

    if artifact is not None or not target.is_file() or not matches(target.read_bytes()):
        if artifact is not None:
            data = artifact.read_bytes()
        else:
            with urlopen(resource["downloadUrl"], timeout=30) as download:
                data = download.read(resource["bytes"] + 1)
        if not matches(data):
            raise ValueError("Create Style Foundry archive does not match the published checksum")
        target.parent.mkdir(parents=True, exist_ok=True)
        with TemporaryDirectory(dir=target.parent) as directory:
            staged = Path(directory) / target.name
            staged.write_bytes(data)
            staged.replace(target)

    order["loadOrder"] = [
        pack for pack in order.get("loadOrder", []) if pack not in (OLD_PACK, target.name)
    ] + [target.name]
    order_path.write_text(json.dumps(order, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def install(client=None, server=None, artifact=None):
    instances = {instance.resolve() for instance in (client, server) if instance is not None}
    for instance in instances:
        mod_jar(instance, "TinkersConstruct-Unofficial-Port-1.21.1-*-NeoForge.jar")
        mod_jar(instance, "create-1.21.1-*.jar")

    if client is not None:
        install_resource_pack(client, artifact)

    for instance in instances:
        shutil.copytree(HERE / "kubejs", instance / "kubejs", dirs_exist_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path)
    parser.add_argument("--server", type=Path)
    parser.add_argument("--resource-pack", type=Path, help="Use the matching GitHub release ZIP from disk.")
    args = parser.parse_args()
    if not (args.client or args.server):
        parser.error("provide a prepared --client, --server, or both")
    if args.resource_pack and not args.client:
        parser.error("--resource-pack requires --client")
    install(args.client, args.server, args.resource_pack)
