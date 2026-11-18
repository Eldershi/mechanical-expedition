#!/usr/bin/env python3
"""Build the client-only NeoForge adapters against a Minecraft 1.21.1 instance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parent
VERSION = "1.0.0"
ADAPTERS = {
    "stock": {
        "id": "expedition_stock_keeper_tooltip_fix",
        "filename": "expedition-stock-keeper-tooltip-fix",
        "name": "Expedition Stock Keeper Tooltip Fix",
        "package": "expedition.storage.mixin",
        "mixins": ["StockKeeperTooltipMixin"],
        "deps": {"create": "6.0.10"},
    },
    "teams": {
        "id": "expedition_ftb_teams_client_compat",
        "filename": "expedition-ftb-teams-client-compat",
        "name": "Expedition FTB Teams Client Compatibility",
        "package": "expedition.ftbteamscompat.mixin",
        "mixins": ["ClientIdentityMixin", "InvitationSortMixin"],
        "deps": {"ftbteams": "2101.1.12"},
    },
    "chunky": {
        "id": "expedition_chunky_guard",
        "filename": "expedition-chunky-startup-guard",
        "name": "Expedition DH / Chunky Startup Guard",
        "package": "expedition.compat.chunky",
        "mixins": ["ChunkyStartupGuard"],
        "deps": {"distanthorizons": "3.3.3", "chunky": "1.4.23"},
    },
    "performance": {
        "id": "expedition_client_performance",
        "filename": "expedition-client-performance",
        "name": "Expedition Client Performance",
        "package": "expedition.performance.client",
        "mixins": ["DhQueueBackoff"],
        "deps": {"distanthorizons": "3.3.3"},
    },
    "tooltips": {
        "id": "expedition_item_tooltips",
        "filename": "expedition-item-tooltips",
        "name": "Expedition Item Tooltips",
        "loader": "javafml",
        "deps": {},
    },
    "recipe-routes": {
        "id": "expedition_recipe_route_labels",
        "filename": "expedition-recipe-route-labels",
        "name": "Expedition Recipe Route Labels",
        "loader": "javafml",
        "deps": {"jei": "19.64.0.455"},
    },
    "planner": {
        "id": "expedition_tool_planner",
        "filename": "expedition-tool-planner",
        "name": "Expedition Foundry Tool Planner",
        "loader": "javafml",
        "chooser": "expedition.toolplanner",
        "deps": {"modernfoundry": "1.21.1-1.6.1-NeoForge"},
    },
    "spells": {
        "id": "expedition_spell_catalog",
        "filename": "expedition-spell-catalog",
        "name": "Expedition Spell Catalog",
        "loader": "javafml",
        "version": "1.0.1",
        "package": "expedition.spellcatalog.mixin",
        "mixins": ["SpellPreviewSkin", "SpellStatAccess", "PreviewProjectionAccess",
                   "SpellPonderIndexBridge", "SpellPonderTagNavigation", "SpellPonderTagText",
                   "PonderTagIconAccess"],
        "deps": {"iss_ponder": "1.0.3", "irons_spellbooks": "1.21.1-3.16.3",
                 "ponder": "1.0.87+mc1.21.1"},
    },
}


def build(adapter, classes, output):
    mod_id = adapter["id"]
    version = adapter.get("version", VERSION)
    config = f"{mod_id}.mixins.json"
    metadata = f'''modLoader = "{adapter.get("loader", "lowcodefml")}"
loaderVersion = "[1,)"
license = "MIT"

[[mods]]
modId = "{mod_id}"
version = "{version}"
displayName = "{adapter["name"]}"
'''
    if adapter.get("mixins"):
        metadata += f'''
[[mixins]]
config = "{config}"
'''
    for dependency, required_version in {"minecraft": "1.21.1", **adapter["deps"]}.items():
        metadata += f'''
[[dependencies.{mod_id}]]
modId = "{dependency}"
type = "required"
versionRange = "[{required_version}]"
ordering = "NONE"
side = "CLIENT"
'''
    jar = output / f'{adapter["filename"]}-neoforge-{version}.jar'
    resources = {"META-INF/neoforge.mods.toml": metadata}
    if adapter.get("mixins"):
        resources[config] = json.dumps({
            "required": True, "minVersion": "0.8.7", "compatibilityLevel": "JAVA_21",
            "package": adapter["package"], "client": adapter["mixins"],
            "injectors": {"defaultRequire": 1},
        })
    resources["pack.mcmeta"] = json.dumps({"pack": {"pack_format": 34, "description": adapter["name"]}})
    resource_roots = [ROOT / "resources" / mod_id]
    if adapter.get("chooser"):
        resource_roots.append(ROOT / "resources" / "chooser")
    for extra in resource_roots:
        for path in sorted(extra.rglob("*")):
            if path.is_file():
                resources[path.relative_to(extra).as_posix()] = path.read_bytes()
    with ZipFile(jar, "w") as archive:
        for name, contents in resources.items():
            archive.writestr(ZipInfo(name), contents, compress_type=ZIP_DEFLATED)
        for path in sorted(classes.rglob("*.class")):
            archive.writestr(ZipInfo(path.relative_to(classes).as_posix()), path.read_bytes(),
                             compress_type=ZIP_DEFLATED)
    return jar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mods", required=True, type=Path)
    parser.add_argument("--libraries", required=True, type=Path, action="append")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--java-home", required=True, type=Path)
    parser.add_argument("--adapter", choices=ADAPTERS, action="append")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    libraries = [jar for root in args.libraries for jar in sorted(root.rglob("*.jar"))]
    classpath = sorted(args.mods.glob("*.jar")) + libraries
    for name in args.adapter or ADAPTERS:
        adapter = ADAPTERS[name]
        with TemporaryDirectory() as temp:
            work = Path(temp)
            classes = work / "classes"
            classes.mkdir()
            sources = sorted((ROOT / "src" / name).rglob("*.java"))
            if adapter.get("chooser"):
                # Each JAR needs its own package in the NeoForge module layer.
                template = ROOT / "src/chooser/expedition/choice/ChoiceScreen.java"
                chooser = work / template.name
                chooser.write_text(template.read_text(encoding="utf-8").replace(
                    "package expedition.choice;", f'package {adapter["chooser"]};', 1), encoding="utf-8")
                sources.append(chooser)
            adapter_classpath = list(classpath)
            if name == "spells":
                # The spell preview mod supplies the selected nested Ponder API.
                ponder = f'ponder-neoforge-{adapter["deps"]["ponder"]}.jar'
                if not any(path.name == ponder for path in adapter_classpath):
                    provider = args.mods / f'iss_ponder-neoforge1.21.1-{adapter["deps"]["iss_ponder"]}.jar'
                    with ZipFile(provider) as jar:
                        path = work / ponder
                        path.write_bytes(jar.read(f"META-INF/jarjar/{ponder}"))
                        adapter_classpath.append(path)
            result = subprocess.run([args.java_home / "bin/javac", "--release", "21", "-proc:none",
                                     "-encoding", "UTF-8", "-cp", os.pathsep.join(map(str, adapter_classpath)),
                                     "-d", classes, *sources])
            if result.returncode:
                raise SystemExit(f"Could not compile the {name} adapter")
            jar = build(adapter, classes, args.output)
            with jar.open("rb") as stream:
                print(hashlib.file_digest(stream, "sha256").hexdigest(), jar.name)


if __name__ == "__main__":
    main()
