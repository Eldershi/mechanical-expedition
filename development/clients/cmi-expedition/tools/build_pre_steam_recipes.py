"""Add native pre-steam recipes alongside CMI recipes, using installed JARs.

The explicit output allowlist bounds the change. Existing recipe scripts and
CMI items are never rewritten; every added recipe uses an expedition ID.
"""
from pathlib import Path
import hashlib
import io
import json
import shutil
import tomllib
import zipfile


ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / "clients/cmi-expedition/instance"
SERVER = ROOT / "servers/cmi-expedition/instance"
OVERLAY = ROOT / "clients/cmi-expedition/overlay"
EVIDENCE = ROOT / "clients/cmi-expedition/evidence/pre-steam-rollback-20261018"
BACKUP = ROOT / "backups/pre-steam-rollback-20261018"

GROUPS = {
    "minecraft": """furnace stonecutter blast_furnace hopper chest bucket glass_bottle paper
        repeater comparator dispenser dropper piston observer""".split(),
    "create": """water_wheel large_water_wheel windmill_bearing cogwheel large_cogwheel
        gearbox vertical_gearbox depot mechanical_press mechanical_mixer encased_fan
        mechanical_bearing mechanical_piston gantry_carriage weighted_ejector millstone
        mechanical_harvester mechanical_plough mechanical_roller deployer mechanical_saw
        mechanical_drill cart_assembler clockwork_bearing elevator_pulley contraption_controls
        andesite_casing copper_casing fluid_tank item_drain spout smart_fluid_pipe fluid_valve
        hose_pulley mechanical_pump fluid_pipe belt_connector chute item_hatch item_vault
        portable_storage_interface portable_fluid_interface andesite_funnel andesite_tunnel
        brass_funnel brass_tunnel smart_chute packager package_frogport redstone_link stock_link
        stock_ticker redstone_requester factory_gauge andesite_alloy propeller whisk brass_hand
        sail_frame white_sail electron_tube rose_quartz transmitter crafting_blueprint
        empty_schematic redstone_contact powered_latch powered_toggle_latch pulse_repeater
        pulse_extender pulse_timer empty_blaze_burner iron_sheet copper_sheet golden_sheet""".split(),
    "create_connected": """parallel_gearbox six_way_gearbox encased_chain_cogwheel crank_wheel
        large_crank_wheel overstress_clutch fluid_vessel item_silo inventory_access_port
        control_chip sequenced_pulse_generator""".split(),
    "createaddition": "rolling_mill".split(),
    "vintageimprovements": """vibrating_table spring_coiling_machine spring_coiling_machine_wheel
        curving_press centrifuge""".split(),
    "createdieselgenerators": ["basin_lid"],
    "copycats": ["copycat_fluid_pipe"],
    "fluidlogistics": """multi_fluid_tank horizontal_multi_fluid_tank fluid_hatch smart_faucet
        fluid_pump smart_hopper fluid_transporter multi_fluid_access_port fluid_packager""".split(),
    "tconstruct": """grout seared_brick seared_melter seared_heater smeltery_controller
        seared_fuel_tank seared_ingot_tank seared_fuel_gauge seared_ingot_gauge cast_chest pattern""".split(),
    "sophisticatedbackpacks": ["backpack", "upgrade_base"],
    "naturescompass": ["naturescompass"],
    "explorerscompass": ["explorerscompass"],
    "functionalstorage": [
        f"{wood}_{size}" for wood in "oak spruce birch jungle acacia dark_oak mangrove crimson warped cherry".split()
        for size in (1, 2, 4)
    ] + ["fluid_1", "fluid_2", "fluid_4"],
}
TARGETS = {f"{namespace}:{name}" for namespace, names in GROUPS.items() for name in names}
# Only the basic rubber shortcut is restored, not every higher-tier recipe which
# happens to produce rubber as a byproduct.
EXACT_IDS = {"thermal:smelting/cured_rubber_from_smelting"}
FORBIDDEN_OUTPUTS = {
    "create:steam_engine", "create:precision_mechanism", "create:mechanical_arm",
    "create:mechanical_crafter", "create:copper_backtank", "create:display_link",
    "vintageimprovements:vacuum_chamber", "tconstruct:scorched_alloyer",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def recipe_outputs(recipe):
    if recipe.get("type") == "forge:conditional":
        return set().union(*(recipe_outputs(row["recipe"]) for row in recipe["recipes"]))
    values = recipe.get("results", [recipe.get("result")])
    if not isinstance(values, list):
        values = [values]
    return {v if isinstance(v, str) else v.get("item") for v in values if isinstance(v, (str, dict))} - {None}


def primary_outputs(recipe):
    if recipe.get("type") == "forge:conditional":
        return set().union(*(primary_outputs(row["recipe"]) for row in recipe["recipes"]))
    result = recipe.get("result")
    if result is None:
        results = recipe.get("results")
        result = results[0] if isinstance(results, list) and results else None
    return {result if isinstance(result, str) else result.get("item")} if isinstance(result, (str, dict)) else set()


def source_archives(jar):
    with zipfile.ZipFile(jar) as archive:
        yield "", archive
        for name in archive.namelist():
            if name.startswith("META-INF/jarjar/") and name.endswith(".jar"):
                with zipfile.ZipFile(io.BytesIO(archive.read(name))) as nested:
                    yield name, nested


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    sources, recipes, found = {}, [], set()
    jars = sorted((CLIENT / "mods").glob("*.jar"))
    jars.append(SERVER / "libraries/net/minecraft/server/1.20.1-20230612.114412/server-1.20.1-20230612.114412-extra.jar")
    owners = set(GROUPS) | {"thermal"}
    for jar in jars:
        for embedded, archive in source_archives(jar):
            source_name = jar.name + ("!" + embedded if embedded else "")
            namespaces = {"minecraft"} if jar.name.endswith("-extra.jar") else set()
            if "META-INF/mods.toml" in archive.namelist():
                metadata = tomllib.loads(archive.read("META-INF/mods.toml").decode())
                namespaces.update(row["modId"] for row in metadata.get("mods", []))
            selected = []
            for name in sorted(archive.namelist()):
                parts = name.split("/")
                if len(parts) < 4 or parts[0] != "data" or parts[1] not in owners & namespaces or parts[2] != "recipes" or not name.endswith(".json"):
                    continue
                native_id = parts[1] + ":" + "/".join(parts[3:])[:-5]
                raw = archive.read(name)
                recipe = json.loads(raw)
                outputs = recipe_outputs(recipe)
                primary = primary_outputs(recipe)
                if (not primary or not primary <= TARGETS) and native_id not in EXACT_IDS:
                    continue
                # A namespace's native recipes come from its owning content JAR,
                # not another mod's compatibility data. Feature conditions remain
                # in the saved JSON and are evaluated by Forge at load time.
                if outputs & FORBIDDEN_OUTPUTS:
                    raise AssertionError((native_id, outputs))
                selected.append({"id": "expedition:pre_steam/native/" + native_id.replace(":", "/"),
                    "nativeId": native_id, "outputs": sorted(outputs), "json": recipe,
                    "source": source_name, "sourceEntry": name, "sourceJsonSha256": sha(raw)})
                found.update(outputs)
            if selected:
                sources[source_name] = {"path": str(jar.relative_to(ROOT)), "embedded": embedded, "sha256": sha(jar.read_bytes())}
                recipes.extend(selected)
    assert not TARGETS - found, f"Native output missing: {sorted(TARGETS - found)}"
    ids = [row["id"] for row in recipes]
    assert len(ids) == len(set(ids)), "Ambiguous native recipe sources"
    assert all(any(row["nativeId"] == exact for row in recipes) for exact in EXACT_IDS)
    recipes.sort(key=lambda row: row["id"])
    data = {"schemaVersion": 1, "mode": "parallel_native_and_cmi", "targets": sorted(TARGETS), "recipes": recipes}
    relative = "kubejs/config/expedition-pre-steam-recipes.json"
    payload = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    for parent in [CLIENT, SERVER, OVERLAY]:
        path = parent / relative
        if path.exists() and path.read_bytes() != payload:
            backup = BACKUP / path.relative_to(ROOT)
            if not backup.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    (EVIDENCE / "native-sources.json").write_text(json.dumps({"sources": sources,
        "nativeRecipes": len(recipes), "nativeOutputs": len(found), "payloadSha256": sha(payload),
        "note": "Additions only; existing CMI recipe scripts and item registrations retained."}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"recipes": len(recipes), "outputs": len(found), "bytes": len(payload)}))


if __name__ == "__main__":
    main()
