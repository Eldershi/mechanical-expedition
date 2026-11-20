"""Source files shared by the NeoForge client and dedicated-server recipe overlays."""

from pathlib import Path
import shutil

PORT = Path(__file__).resolve().parents[1]
INDUSTRY = PORT / "industry"
MATERIALS = PORT / "cmi-materials"
BRASS = PORT / "world-server/brass-industry/overlay"
DEPOSITS = PORT / "world-server/deposits/overlay"
ITEM_COMPATIBILITY = PORT / "world-server/item-compatibility/overlay"
RADAR = PORT / "radar-mbd2"
RECIPE_TYPES = PORT / "world-server/brass-industry/recipe-types"

SHARED = {
    Path(name): INDUSTRY / name
    for name in (
        "kubejs/server_scripts/ExpeditionControlComponents.js",
        "kubejs/server_scripts/ExpeditionElectricalProgression.js",
        "kubejs/server_scripts/ExpeditionFactoryFoundations.js",
        "kubejs/server_scripts/ExpeditionIndustry.js",
        "kubejs/server_scripts/ExpeditionLunarSilicon.js",
        "kubejs/server_scripts/ExpeditionManufacturingContinuity.js",
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
for name in ("CmiDeposits.js", "CmiIndustrialMaterials.js", "CmiProcessFluids.js"):
    SHARED[Path("kubejs/startup_scripts/cmi") / name] = MATERIALS / name
BRASS_RECIPES = Path("kubejs/server_scripts/ExpeditionBrassIndustryRecipes.js")
SHARED[BRASS_RECIPES] = BRASS / BRASS_RECIPES
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
        Path("kubejs/client_scripts/ExpeditionMineralChemistryLanguage.js"),
        Path("kubejs/client_scripts/ExpeditionSugarSyrupLanguage.js"),
    )
}

SPACE_MOD = "expedition-space-neoforge-1.0.1.jar"
ITEM_COMPATIBILITY_MOD = "expedition-item-compatibility-neoforge-1.0.0.jar"
REQUIRED_MODS = (SPACE_MOD, ITEM_COMPATIBILITY_MOD)


def files(client):
    return SHARED | CLIENT if client else SHARED


def install_files(instance, client=False):
    for relative, source in files(client).items():
        destination = instance / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
