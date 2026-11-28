"""Shared production files and settings for NeoForge clients and dedicated servers."""

from hashlib import sha256
import json
from pathlib import Path
import shutil
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
        "kubejs/server_scripts/ExpeditionGasPhases.js",
        "kubejs/server_scripts/ExpeditionGasSampleTasks.js",
        "kubejs/server_scripts/ExpeditionOilProgression.js",
        "kubejs/server_scripts/ExpeditionPolymerProgression.js",
        "kubejs/server_scripts/ExpeditionSiliconeProgression.js",
        "kubejs/startup_scripts/ExpeditionGasMaterials.js",
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
TRADE_CONTROLLER = Path("kubejs/data/expedition_industry/recipe/controller/trading_station_early.json")
SHARED[TRADE_CONTROLLER] = BRASS / TRADE_CONTROLLER
for name in ("lightmanscurrency-common.txt", "lightmanscurrency-server.txt"):
    relative = Path("config") / name
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
        Path("kubejs/client_scripts/ExpeditionGasLanguage.js"),
        Path("kubejs/client_scripts/ExpeditionMineralChemistryLanguage.js"),
        Path("kubejs/client_scripts/ExpeditionRockGeneratorInfo.js"),
        Path("kubejs/client_scripts/ExpeditionSugarSyrupLanguage.js"),
    )
}

FOUNDRY_BIODIESEL_FUEL = Path("kubejs/data/expedition/recipe/tconstruct/fuel/biodiesel.json")
SHARED[FOUNDRY_BIODIESEL_FUEL] = ROOT / "current/server" / FOUNDRY_BIODIESEL_FUEL

SERVERCORE_CONFIG = Path("config/servercore/config.yml")
SERVER = {SERVERCORE_CONFIG: ROOT / "current/server" / SERVERCORE_CONFIG}

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
    for name in ("Expedition_CMI_alloy_furnace_andesite", "Expedition_CMI_alloy_furnace_brass", "Expedition_CMI_hydropress",
                 "Expedition_CMI_shaft_furnace", "Expedition_CMI_electrolytic_cell", "Expedition_CMI_trading_station")
    for source in (PORT / "create-blueprints/schematics" / f"{name}.nbt",)
})
CLIENT.update(INDUSTRIAL_VISUALS)
SHARED.update({
    path: source for path, source in INDUSTRIAL_VISUALS.items()
    if path.parts[1:4] == ("assets", "expedition_industry", "lang")
})


SPACE_MOD = "expedition-space-neoforge-1.0.1.jar"
ITEM_COMPATIBILITY_MOD = "expedition-item-compatibility-neoforge-1.0.0.jar"
REFINERY_GAS_MOD = "expedition-refinery-steam-compat-neoforge-1.1.0.jar"
ROCK_GENERATOR_MOD = "expedition-rock-generator-neoforge-1.0.0.jar"
ALLOY_FURNACE_MOD = "expedition-alloy-furnace-neoforge-1.0.0.jar"
STRUCTURE_LOOKUP_MOD = "expedition-structure-lookup-neoforge-1.0.0.jar"
VILLAGE_TREE_LOOKUP_MOD = "expedition-village-tree-lookup-neoforge-1.0.0.jar"
SIFT_COMPAT_MOD = "expedition-sift-compat-neoforge-1.0.0.jar"
CREATE_NUCLEAR_MOD = "createnuclear-2.0.1-neoforge.jar"
PROGRESSION_DOWNLOADS = {
    "createnuclear": CREATE_NUCLEAR_MOD,
    "creategearsandtavern": "creategearsandtavern-1.2.0-1.21.1.jar",
    "lightmanscurrency": "lightmanscurrency-1.21-2.3.0.6.jar",
    "the_sift": "mielon-s-the-sift-2.0.6-mc1.21.1-neo.jar",
}
SPACE_INSTALL_ADAPTERS = (SPACE_MOD, ITEM_COMPATIBILITY_MOD, ROCK_GENERATOR_MOD, ALLOY_FURNACE_MOD, SIFT_COMPAT_MOD)
REQUIRED_MODS = (*SPACE_INSTALL_ADAPTERS, STRUCTURE_LOOKUP_MOD, VILLAGE_TREE_LOOKUP_MOD,
                 *PROGRESSION_DOWNLOADS.values())
THERMAL_STYLE = "thermal-create-style.json"
PAXI_ORDER = Path("config/paxi/resourcepack_load_order.json")
QUARK_CONFIG = Path("config/quark-common.toml")
SHARED[QUARK_CONFIG] = ROOT / "current/client" / QUARK_CONFIG


def files(client):
    return SHARED | (CLIENT if client else SERVER)


def install_files(instance, client=False):
    for relative, source in files(client).items():
        destination = instance / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if client:
        (instance / "mods/expedition-alloy-furnace-render-neoforge-1.0.0.jar").unlink(missing_ok=True)


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
    catalog = json.loads((PORT / "community-mods.json").read_text(encoding="utf-8"))
    for mod, filename in PROGRESSION_DOWNLOADS.items():
        entry = catalog[mod]
        for instance in (client, server):
            fetch_verified(instance / "mods" / filename, entry["file"]["url"], entry["sha256"])
    resource = thermal_style_resource()
    fetch_verified(client / resource["path"], resource["downloadUrl"], resource["sha256"])
    order_file = client / PAXI_ORDER
    order = json.loads(order_file.read_text(encoding="utf-8")) if order_file.is_file() else {}
    enable_thermal_style(order)
    order_file.write_text(json.dumps(order, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
