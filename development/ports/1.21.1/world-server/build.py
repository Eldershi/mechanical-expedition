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
    "motion-guard": ("expedition_player_motion_guard", "1.1.0", "Expedition Player Motion Guard",
                     "expedition.motionguard.mixin", ["PlayerMotionMixin", "TeleportObservationMixin"]),
    "teleport": ("expedition_teleport_fix", "1.0.0", "Expedition Async Teleport",
                 "expedition.teleport.mixin", ["TeleportCommandMixin"]),
}
COMMON_DIAGNOSTICS = ("BoundedRing", "DiagnosticsConfig", "DurableJsonLog", "JfrRecorder", "PlayerSnapshot")


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


def build(module, java, cp, output):
    modid, version, title, mixins_package, mixins = MODULES[module]
    side = "BOTH" if module == "alpine" else "SERVER"
    filename = f"{modid.replace('_', '-')}-neoforge-{version}.jar"
    sources = sorted((HERE / module / "src").rglob("*.java"))
    with tempfile.TemporaryDirectory() as temp:
        classes = Path(temp)
        if module == "motion-guard":
            shared = MOTION / "src/expedition/motionguard"
            sources.extend(shared / "diagnostics" / f"{name}.java" for name in COMMON_DIAGNOSTICS)
            sources += [shared / "MotionPolicy.java", MOTION / "tests/MotionPolicyTest.java"]
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
[[mixins]]
config="{mixin_config}"
'''
        config = {"required": True, "minVersion": "0.8", "package": mixins_package,
                  "compatibilityLevel": "JAVA_21", "mixins": mixins, "injectors": {"defaultRequire": 1}}
        output.mkdir(parents=True, exist_ok=True)
        path = output / filename
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as jar:
            jar.writestr(ZipInfo("META-INF/neoforge.mods.toml"), metadata, compress_type=ZIP_DEFLATED)
            jar.writestr(ZipInfo(mixin_config), json.dumps(config) + "\n", compress_type=ZIP_DEFLATED)
            if module == "alpine":
                policy = HERE.parents[2] / "design/tectonic-preview-20261018/v2/climate/biome-policy.json"
                jar.writestr(ZipInfo("alpine-biome-policy.json"), policy.read_bytes(),
                             compress_type=ZIP_DEFLATED)
            for source in sorted((classes / "expedition").rglob("*.class")):
                jar.writestr(ZipInfo(source.relative_to(classes).as_posix()), source.read_bytes(),
                             compress_type=ZIP_DEFLATED)
        print(path)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--java", type=Path, required=True)
    p.add_argument("--server", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("modules", choices=tuple(MODULES), nargs="+")
    options = p.parse_args()
    cp = classpath(options.server.resolve())
    for module in options.modules:
        build(module, options.java.resolve(), cp, options.output.resolve())
