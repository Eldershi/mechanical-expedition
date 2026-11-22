"""Shared production files and settings for NeoForge clients and dedicated servers."""

from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import tomllib
from tempfile import TemporaryDirectory
from urllib.request import urlopen

PORT = Path(__file__).resolve().parents[1]
ROOT = PORT.parents[2]
INDUSTRY = PORT / "industry"
MATERIALS = PORT / "cmi-materials"
BRASS = PORT / "world-server/brass-industry/overlay"
DEPOSITS = PORT / "world-server/deposits/overlay"
ITEM_COMPATIBILITY = PORT / "world-server/item-compatibility/overlay"
RADAR = PORT / "radar-mbd2"
RECIPE_TYPES = PORT / "world-server/brass-industry/recipe-types"
INDUSTRIAL_MACHINES = BRASS.parent / "visuals/multiblock"

SHARED = {
    Path(name): INDUSTRY / name
    for name in (
        "kubejs/server_scripts/ExpeditionControlComponents.js",
        "kubejs/server_scripts/ExpeditionElectricalProgression.js",
        "kubejs/server_scripts/ExpeditionFactoryFoundations.js",
        "kubejs/server_scripts/ExpeditionIndustry.js",
        "kubejs/server_scripts/ExpeditionLunarSilicon.js",
        "kubejs/server_scripts/ExpeditionManufacturingContinuity.js",
        "kubejs/server_scripts/ExpeditionMechanismProgression.js",
        "kubejs/server_scripts/ExpeditionMetallurgy.js",
        "kubejs/server_scripts/ExpeditionMineralChemistry.js",
        "kubejs/server_scripts/ExpeditionPlantAsh.js",
        "kubejs/server_scripts/ExpeditionPlating.js",
        "kubejs/server_scripts/ExpeditionSpaceManufacturing.js",
        "kubejs/server_scripts/ExpeditionSyrupRecipes.js",
        "kubejs/server_scripts/ExpeditionVanadium.js",
        "kubejs/server_scripts/ExpeditionWasteProcessing.js",
        "kubejs/startup_scripts/ExpeditionSugarSyrup.js",
        "kubejs/data/expedition/recipe/factory/space/press_single_crystal_silicon.json",
        "kubejs/data/createcraftedbeginning/tags/item/press_head_tools.json",
    )
}
for name in ("CmiDeposits.js", "CmiIndustrialMaterials.js", "CmiMechanisms.js", "CmiProcessFluids.js"):
    SHARED[Path("kubejs/startup_scripts/cmi") / name] = MATERIALS / name
for script in ("ExpeditionBrassIndustryRecipes.js", "ExpeditionAlloyFurnaceHeat.js"):
    relative = Path("kubejs/server_scripts") / script
    SHARED[relative] = BRASS / relative
RADAR_RECIPES = Path("kubejs/server_scripts/RadarAcquisition.js")
SHARED[RADAR_RECIPES] = RADAR / RADAR_RECIPES
SHARED.update({
    source.relative_to(DEPOSITS): source
    for source in sorted((DEPOSITS / "kubejs").rglob("*"))
    if source.is_file()
})
SHARED.update({
    Path(name): ITEM_COMPATIBILITY / name
    for name in ("kubejs/data/expedition/item_compatibility.json",
                 "kubejs/server_scripts/ExpeditionItemCompatibilityTags.js")
})
SHARED.update({
    Path("ldlib2/assets/mbd2/recipe_type") / source.name: source
    for source in sorted(RECIPE_TYPES.glob("*.rt"))
})

CLIENT = {
    path: INDUSTRY / path
    for path in (
        Path("kubejs/assets/cmi/textures/item/mechanism/complete/andesite.png"),
        Path("kubejs/assets/createnuclear/sounds.json"),
        Path("kubejs/client_scripts/ExpeditionMineralChemistryLanguage.js"),
        Path("kubejs/client_scripts/ExpeditionRockGeneratorInfo.js"),
        Path("kubejs/client_scripts/ExpeditionSugarSyrupLanguage.js"),
    )
}

INDUSTRIAL_VISUALS = {
    relative: source
    for folder in ("assets", "client_scripts")
    for source in sorted((BRASS / "kubejs" / folder).rglob("*"))
    if source.is_file()
    for relative in (source.relative_to(BRASS),)
}
INDUSTRIAL_DEFINITIONS = {
    Path("ldlib2/assets/mbd2/multiblock") / source.name: source
    for source in sorted(INDUSTRIAL_MACHINES.glob("*.mb"))
}
INDUSTRIAL_DEFINITIONS.update({
    Path("ldlib2/assets/mbd2/recipe_type") / recipe.name: recipe
    for machine in INDUSTRIAL_MACHINES.glob("*.mb")
    for recipe in (RECIPE_TYPES / f"expedition_{machine.stem}.rt",)
})
INDUSTRIAL_DEFINITIONS.update({
    Path("ldlib2/assets/ldlib2/resources/global") / source.name: source
    for source in sorted((BRASS.parent / "visuals/predicates").glob("*.predicate.nbt"))
})
SHARED.update(INDUSTRIAL_DEFINITIONS)
CLIENT.update({
    Path("schematics") / source.name: source
    for source in sorted((PORT / "create-blueprints/schematics").glob("Expedition_CMI_alloy_furnace_*.nbt"))
})
CLIENT.update(INDUSTRIAL_VISUALS)
SHARED.update({
    path: source for path, source in INDUSTRIAL_VISUALS.items()
    if path.parts[1:4] == ("assets", "expedition_industry", "lang")
})


SPACE_MOD = "expedition-space-neoforge-1.0.1.jar"
ITEM_COMPATIBILITY_MOD = "expedition-item-compatibility-neoforge-1.0.0.jar"
ROCK_GENERATOR_MOD = "expedition-rock-generator-neoforge-1.0.0.jar"
ALLOY_FURNACE_MOD = "expedition-alloy-furnace-neoforge-1.0.0.jar"
REQUIRED_MODS = (SPACE_MOD, ITEM_COMPATIBILITY_MOD, ROCK_GENERATOR_MOD, ALLOY_FURNACE_MOD)
CREATE_NUCLEAR_MOD = "createnuclear-2.0.1-neoforge.jar"
THERMAL_STYLE = "thermal-create-style.json"
PAXI_ORDER = Path("config/paxi/resourcepack_load_order.json")
QUARK_CONFIG = Path("config/quark-common.toml")


def disable_scaffolding_replacement(payload):
    updated, count = re.subn(rb'(?m)^([ \t]*"Replace Scaffolding"[ \t]*=[ \t]*)(?:true|false)\b',
                             rb'\g<1>false', payload)
    if count != 1 or tomllib.loads(updated.decode("utf-8-sig")).get("tweaks", {}).get("Replace Scaffolding") is not False:
        raise ValueError(f"Expected the Replace Scaffolding setting in {QUARK_CONFIG}")
    return updated


def files(client):
    return SHARED | CLIENT if client else SHARED


def install_files(instance, client=False):
    for relative, source in files(client).items():
        destination = instance / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if client:
        (instance / "mods/expedition-alloy-furnace-render-neoforge-1.0.0.jar").unlink(missing_ok=True)
    config = instance / QUARK_CONFIG
    config.parent.mkdir(parents=True, exist_ok=True)
    if config.exists():
        config.write_bytes(disable_scaffolding_replacement(config.read_bytes()))
    else:
        config.write_bytes(b'[tweaks]\n"Replace Scaffolding" = false\n')


def thermal_style_resource():
    integration = ROOT / "integrations/resourcepacks" / THERMAL_STYLE
    resource, = json.loads(integration.read_text(encoding="utf-8"))["clientFiles"]
    return resource


def enable_thermal_style(order):
    pack = Path(thermal_style_resource()["path"]).name
    order["loadOrder"] = [name for name in order.get("loadOrder", []) if name != pack] + [pack]


def fetch_verified(target, url, checksum):
    if target.is_file() and sha256(target.read_bytes()).hexdigest() == checksum:
        return
    with urlopen(url, timeout=30) as response:
        data = response.read()
    if sha256(data).hexdigest() != checksum:
        raise ValueError(f"Checksum mismatch for {target.name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=target.parent) as directory:
        staged = Path(directory) / target.name
        staged.write_bytes(data)
        staged.replace(target)


def install_progression_downloads(client, server):
    entry = json.loads((PORT / "community-mods.json").read_text(encoding="utf-8"))["createnuclear"]
    for instance in (client, server):
        fetch_verified(instance / "mods" / CREATE_NUCLEAR_MOD, entry["file"]["url"], entry["sha256"])
    resource = thermal_style_resource()
    fetch_verified(client / resource["path"], resource["downloadUrl"], resource["sha256"])
    order_file = client / PAXI_ORDER
    order = json.loads(order_file.read_text(encoding="utf-8")) if order_file.is_file() else {}
    enable_thermal_style(order)
    order_file.write_text(json.dumps(order, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
