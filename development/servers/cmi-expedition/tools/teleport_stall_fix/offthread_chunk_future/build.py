"""Build an isolated candidate; never install or mutate the running payload."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

BASE = Path(__file__).resolve().parent
SERVER = BASE.parents[2]
BUILD = BASE / "build"
CLASSES = BUILD / "classes"
TEST_CLASSES = BUILD / "test-classes"
JAR = BUILD / "expedition-chunk-future-1.0.0-candidate.jar"


def run(command, logfile):
    result = subprocess.run(command, capture_output=True, text=True)
    (BUILD / logfile).write_text(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError(f"Command failed; see {BUILD / logfile}\n{result.stderr}")
    return result.stdout


def main():
    BUILD.mkdir(exist_ok=True)
    for path in (CLASSES, TEST_CLASSES):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir()
    libraries_root = SERVER / "instance/libraries"
    minecraft = libraries_root / "net/minecraft/server/1.20.1-20230612.114412/server-1.20.1-20230612.114412-srg.jar"
    dependencies = [minecraft]
    dependencies.extend(sorted(p for p in libraries_root.rglob("*.jar")
                               if "net/minecraft/" not in str(p) and zipfile.is_zipfile(p)))
    # Some downloaded server-library entries are empty placeholders. Read the
    # already-installed launcher dependency copies rather than downloading files.
    launcher_libraries = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries')
    for group in ("com/mojang/datafixerupper", "com/google/code/gson", "com/google/guava",
                  "org/spongepowered/mixin", "org/slf4j/slf4j-api", "it/unimi/dsi/fastutil"):
        dependencies.extend(sorted(p for p in (launcher_libraries / group).rglob("*.jar")
                                   if zipfile.is_zipfile(p)))
    classpath = ":".join(map(str, dependencies))
    sources = sorted((BASE / "src").rglob("*.java"))
    run(["javac", "--release", "17", "-proc:none", "-encoding", "UTF-8",
         "-cp", classpath, "-d", str(CLASSES), *map(str, sources)], "compile.log")
    test_cp = str(CLASSES) + ":" + classpath
    run(["javac", "--release", "17", "-proc:none", "-cp", test_cp,
         "-d", str(TEST_CLASSES), str(BASE / "tests/FutureSchedulingRegression.java")],
        "test-compile.log")
    test_output = run(["java", "-cp", str(TEST_CLASSES) + ":" + test_cp,
                       "FutureSchedulingRegression"], "test.log")
    # Save the exact integration evidence supporting use of the existing API.
    run(["javap", "-classpath", str(minecraft), "-p", "-c",
         "net.minecraft.server.level.ServerChunkCache"], "minecraft-ServerChunkCache.javap.txt")
    radium = next((SERVER / "instance/mods").glob("radium-*.jar"))
    run(["javap", "-classpath", str(radium), "-p", "-c",
         "me.jellysquid.mods.lithium.mixin.world.chunk_access.ServerChunkManagerMixin"],
        "radium-ServerChunkManagerMixin.javap.txt")
    run(["javap", "-classpath", str(CLASSES) + ":" + classpath, "-p", "-c", "-v",
         "expedition.chunkfuture.mixin.OffThreadStructureChunkMixin"], "candidate-mixin.javap.txt")
    config = {
        "required": True, "minVersion": "0.8",
        "package": "expedition.chunkfuture.mixin", "compatibilityLevel": "JAVA_17",
        "mixins": ["OffThreadStructureChunkMixin"], "injectors": {"defaultRequire": 1}
    }
    with zipfile.ZipFile(JAR, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("META-INF/MANIFEST.MF",
                         "Manifest-Version: 1.0\nMixinConfigs: expedition-chunkfuture.mixins.json\n\n")
        archive.writestr("pack.mcmeta", json.dumps({"pack": {
            "pack_format": 15, "description": "Expedition off-thread structure chunk scheduling"}}))
        archive.writestr("expedition-chunkfuture.mixins.json", json.dumps(config, indent=2))
        archive.writestr("META-INF/mods.toml", '''modLoader="lowcodefml"
loaderVersion="[47,)"
license="Private modpack compatibility patch"
[[mods]]
modId="expedition_chunk_future"
version="1.0.0"
displayName="Expedition Off-thread Structure Chunk Future"
[[dependencies.expedition_chunk_future]]
modId="minecraft"
mandatory=true
versionRange="[1.20.1,1.20.2)"
''')
        for path in CLASSES.rglob("*.class"):
            archive.write(path, str(path.relative_to(CLASSES)))
    verification = {
        "candidate": str(JAR), "sha256": hashlib.sha256(JAR.read_bytes()).hexdigest(),
        "radiumSource": str(radium),
        "radiumSha256": hashlib.sha256(radium.read_bytes()).hexdigest(),
        "minecraftSource": str(minecraft), "compiled": True,
        "concurrencyRegression": test_output.strip(),
        "mixinConfig": "expedition-chunkfuture.mixins.json",
        "mixinClass": "expedition.chunkfuture.mixin.OffThreadStructureChunkMixin",
        "interception": "off-owner-thread AND create=true AND STRUCTURE_STARTS only",
        "loadTicket": "unique request ID; no timeout; exact requested status level; main-thread add/remove; finally cleanup",
        "preserves": ["same chunk generation pipeline", "same coordinates and status",
                      "mandatory missing and exceptional generation failure", "railway structure avoidance"],
        "runtimeForgeIntegrationTested": False, "installed": False,
        "knownLimit": "Does not async-prepare main-thread teleport destination chunks by itself"
    }
    (BUILD / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(json.dumps(verification, indent=2))


if __name__ == "__main__":
    main()
