#!/usr/bin/env python3
"""Build the server adapters against a NeoForge 1.21.1 installation."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


HERE = Path(__file__).resolve().parent
MOTION = HERE.parents[2] / "tools/player-motion-guard"
MODULES = {
    "alpine": ("expedition_alpine_climate", "1.0.0", "Expedition Local Alpine Climate",
               "expedition.alpine.mixin", ["BiomeTemperatureMixin", "BiomeTemperatureAccess", "SurfaceSystemMixin"]),
    "equipment": ("expedition_equipment_rules", "1.0.0", "Expedition Curios Equipment", "", []),
    "ie-machine": ("expedition_ie_machine_compat", "1.0.0", "Expedition IE Machine Compatibility",
                   "expedition.iemachines.mixin", ["CokeOvenCapacityMixin", "FluidPipeConnectionMixin"]),
    "island-rail": ("expedition_island_rail_transfer", "1.0.0", "Expedition Island Rail Transfer", "", []),
    "motion-guard": ("expedition_player_motion_guard", "1.1.0", "Expedition Player Motion Guard",
                     "expedition.motionguard.mixin", ["PlayerMotionMixin", "TeleportObservationMixin"]),
    "railway": ("expedition_railway_avoidance", "1.0.0", "Expedition Railway Avoidance",
                "expedition.railway.mixin", ["StructureStageMixin", "StructureCandidateMixin", "RailwayPlannerMixin"]),
    "teleport": ("expedition_teleport_fix", "1.0.0", "Expedition Async Teleport",
                 "expedition.teleport.mixin", ["TeleportCommandMixin"]),
    "space": ("expedition_space", "1.0.0", "Expedition Earth–Moon Logistics",
              "expedition.space.mixin", ["BreathingReserveMixin", "OtherPadMixin"]),
    "twilight": ("expedition_worldgen_compat", "1.1.1", "Expedition Twilight Landmarks",
                 "expedition.twilight.mixin", ["MagicMapMixin", "LocateMixin"]),
    "world-rules": ("expedition_world_rules", "1.0.0", "Expedition World Rules", "", []),
}
COMMON_DIAGNOSTICS = ("BoundedRing", "DiagnosticsConfig", "DurableJsonLog", "JfrRecorder", "PlayerSnapshot")
DEPENDENCIES = {
    "equipment": ("curios", "[9.5.1,10)", "curios-neoforge-9.5.1+1.21.1.jar"),
    "ie-machine": ("immersiveengineering", "[12.4.2-194]", "ImmersiveEngineering-1.21.1-12.4.2-194.jar"),
    "island-rail": ("create", "[6.0.10]", "create-1.21.1-6.0.10.jar"),
    "railway": ("tongdarailway", "[1.1.6+mc21.1]", "tongdarailway-1.1.6-mc21.1.jar"),
    "twilight": ("twilightforest", "[4.8.3345]", "twilightforest-1.21.1-4.8.3345-universal.jar"),
}
SPACE_DEPENDENCIES = (
    ("ad_astra", "[1.16.26]", "adastra-1.21.1-1.16.26-neoforge.jar"),
    ("allthemodium", "[3.2.1]", "allthemodium-3.2.1_mc_1.21.1.jar"),
    ("createcraftedbeginning", "[0.1.1]", "createcraftedbeginning-0.1.1.jar"),
    ("mbd2", "[21.1.1.a]", "Multiblocked2-1.21-1.21.1-21.1.1.a-all.jar"),
    ("ldlib2", "[2.2.46.a]", "ldlib2-neoforge-1.21.1-2.2.46.a-all.jar"),
    ("ftbteams", "[2101.1.12]", "ftb-teams-neoforge-2101.1.12.jar"),
)
TWILIGHT_POLICY = HERE.parents[2] / "clients/cmi-expedition/tools/compat/BossDensityPolicy.java"
TWILIGHT_CONFIG = HERE.parents[2] / "servers/cmi-expedition/deployment/config/expedition-boss-density.json"


def classpath(server):
    launch, = server.glob("libraries/net/neoforged/neoforge/21.1.*/unix_args.txt")
    neo_patched, = launch.parent.glob("*-server.jar")
    neo_api, = launch.parent.glob("*-universal.jar")
    vanilla, = (server / "libraries/net/minecraft/server").glob("*/*-srg.jar")
    legacy = next(line.removeprefix("-DlegacyClassPath=")
                  for line in launch.read_text().splitlines()
                  if line.startswith("-DlegacyClassPath="))
    return os.pathsep.join(map(str, (neo_patched, vanilla, neo_api,
                                      *(server / p for p in legacy.split(os.pathsep)))))


def build(module, java, cp, output, mods, space_proof=False):
    modid, version, title, mixins_package, mixins = MODULES[module]
    side = "SERVER" if module in {"island-rail", "motion-guard", "teleport"} else "BOTH"
    filename = f"{modid.replace('_', '-')}-neoforge-{version}.jar"
    sources = sorted((HERE / module / "src").rglob("*.java"))
    if module in DEPENDENCIES:
        dependency_id, dependency_version, dependency_jar = DEPENDENCIES[module]
        cp += os.pathsep + str(mods / dependency_jar)
    if module == "space":
        cp += os.pathsep + os.pathsep.join(str(mods / jar) for _, _, jar in SPACE_DEPENDENCIES)
        if space_proof:
            sources.extend(sorted((HERE / module / "tests").glob("*.java")))
            sources.extend(sorted((HERE / "brass-industry/tests").glob("*.java")))
            cp += os.pathsep + str(mods / "create-1.21.1-6.0.10.jar")
    with tempfile.TemporaryDirectory() as temp:
        classes = Path(temp)
        if module == "island-rail":
            with ZipFile(mods / dependency_jar) as create:
                for entry in create.namelist():
                    if entry.startswith("META-INF/jarjar/") and entry.endswith(".jar"):
                        embedded = classes / Path(entry).name
                        embedded.write_bytes(create.read(entry))
                        cp += os.pathsep + str(embedded)
        if module == "motion-guard":
            shared = MOTION / "src/expedition/motionguard"
            sources.extend(shared / "diagnostics" / f"{name}.java" for name in COMMON_DIAGNOSTICS)
            sources += [shared / "MotionPolicy.java", MOTION / "tests/MotionPolicyTest.java"]
        if module == "twilight":
            sources.append(TWILIGHT_POLICY)
        subprocess.run([str(java), "-m", "jdk.compiler/com.sun.tools.javac.Main", "--release", "21",
                        "-proc:none", "-encoding", "UTF-8", "-cp", cp, "-d", str(classes),
                        *map(str, sources)], check=True)
        if module == "motion-guard":
            subprocess.run([str(java), "-Xverify:all", "-cp", str(classes), "MotionPolicyTest"], check=True)
        mixin_config = modid.replace("_", "-") + ".mixins.json"
        metadata = f'''modLoader="javafml"
loaderVersion="[4,)"
license="See repository license"
[[mods]]
modId="{modid}"
version="{version}"
displayName="{title}"
[[dependencies.{modid}]]
modId="minecraft"
type="required"
versionRange="[1.21.1,1.21.2)"
side="{side}"
[[dependencies.{modid}]]
modId="neoforge"
type="required"
versionRange="[21.1.267,21.2)"
side="{side}"
'''
        if module == "space" and space_proof:
            metadata += '[[mods]]\nmodId="expedition_space_acceptance"\nversion="1.0.0"\ndisplayName="Expedition Space Acceptance"\n'
        if mixins:
            metadata += f'[[mixins]]\nconfig="{mixin_config}"\n'
        module_dependencies = [DEPENDENCIES[module]] if module in DEPENDENCIES else []
        if module == "space":
            module_dependencies = SPACE_DEPENDENCIES
        for dependency_id, dependency_version, _ in module_dependencies:
            metadata += f'''[[dependencies.{modid}]]
modId="{dependency_id}"
type="required"
versionRange="{dependency_version}"
ordering="AFTER"
side="{side}"
'''
        config = {"required": True, "minVersion": "0.8", "package": mixins_package,
                  "compatibilityLevel": "JAVA_21", "mixins": mixins, "injectors": {"defaultRequire": 1}}
        output.mkdir(parents=True, exist_ok=True)
        path = output / filename
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as jar:
            jar.writestr(ZipInfo("META-INF/neoforge.mods.toml"), metadata, compress_type=ZIP_DEFLATED)
            if mixins:
                jar.writestr(ZipInfo(mixin_config), json.dumps(config) + "\n", compress_type=ZIP_DEFLATED)
            if module == "alpine":
                policy = HERE.parents[2] / "design/tectonic-preview-20261018/v2/climate/biome-policy.json"
                jar.writestr(ZipInfo("alpine-biome-policy.json"), policy.read_bytes(),
                             compress_type=ZIP_DEFLATED)
            if module == "twilight":
                write_twilight_sets(jar, mods / dependency_jar)
            resources = HERE / module / "resources"
            for source in sorted(resources.rglob("*")):
                if source.is_file():
                    jar.writestr(ZipInfo(source.relative_to(resources).as_posix()), source.read_bytes(),
                                 compress_type=ZIP_DEFLATED)
            for source in sorted((classes / "expedition").rglob("*.class")):
                jar.writestr(ZipInfo(source.relative_to(classes).as_posix()), source.read_bytes(),
                             compress_type=ZIP_DEFLATED)
        print(path)


def write_twilight_sets(jar, twilight):
    structures = json.loads(TWILIGHT_CONFIG.read_text())["twilightLandmarkFrequencies"]
    with ZipFile(twilight) as original:
        for structure in sorted(structures):
            namespace, path = structure.split(":", 1)
            location = f"data/{namespace}/worldgen/structure_set/{path}.json"
            data = json.loads(original.read(location))
            placement = data["placement"]
            if placement["type"] != "twilightforest:landmark_grid":
                raise ValueError(f"Unexpected placement in {location}")
            placement["type"] = "expedition_worldgen_compat:sparse_landmark"
            placement["structure"] = structure
            jar.writestr(ZipInfo(location), json.dumps(data, indent=2) + "\n", compress_type=ZIP_DEFLATED)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--java", type=Path, required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--mods", type=Path)
    p.add_argument("--space-proof", action="store_true", help="include space acceptance commands for disposable worlds")
    p.add_argument("modules", choices=tuple(MODULES), nargs="+")
    options = p.parse_args()
    cp = classpath(options.server.resolve())
    for module in options.modules:
        build(module, options.java.resolve(), cp, options.output.resolve(),
              (options.mods or options.server / "mods").resolve(), options.space_proof)
