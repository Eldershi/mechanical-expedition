#!/usr/bin/env python3
"""Preserve CSA's fluid registries while Steam Letters owns Create boiler logic."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parent
MODS = ROOT / "staging/mods"
ORIGINAL = "Create-Steam-Ages-1.0.jar"
PATCHED = "Create-Steam-Ages-1.0-expedition-steamletters-compat.jar"
SOURCE_HASH = "d7fc6196f18fa4f83148e5b3e50d7b203662405374e40e3a2bcaa99f646e5148"
backup = ROOT / "downloads/legacy" / ORIGINAL
backup.parent.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(MODS / ORIGINAL, backup)
source_hash = hashlib.sha256(backup.read_bytes()).hexdigest()
assert source_hash == SOURCE_HASH, (source_hash, SOURCE_HASH)
target = MODS / PATCHED
with zipfile.ZipFile(backup) as source, zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as result:
    for entry in source.infolist():
        payload = source.read(entry.filename)
        if entry.filename == "create_steam_ages.mixins.json":
            config = json.loads(payload)
            assert config["mixins"] == ["BoilerDataMixin"]
            config["mixins"] = []
            payload = (json.dumps(config, indent=2) + "\n").encode()
        elif entry.filename == "META-INF/mods.toml":
            text = payload.decode()
            assert 'version = "1.0"' in text
            text = text.replace('version = "1.0"', 'version = "1.0-expedition-sl-compat1"', 1)
            text += '''
[[dependencies."create_steam_ages"]]
modId = "steam_letters"
mandatory = true
versionRange = "[2.0.0]"
ordering = "AFTER"
side = "BOTH"
'''
            payload = text.encode()
        result.writestr(entry, payload)

with zipfile.ZipFile(backup) as source, zipfile.ZipFile(target) as result:
    changed = [name for name in source.namelist() if source.read(name) != result.read(name)]
    assert changed == [name for name in source.namelist() if name in {"create_steam_ages.mixins.json", "META-INF/mods.toml"}], changed
    classes = [name for name in source.namelist() if name.endswith(".class")]
    assert all(source.read(name) == result.read(name) for name in classes)
    assets = [name for name in source.namelist() if name.startswith(("data/", "assets/"))]
    assert all(source.read(name) == result.read(name) for name in assets)

# Keep the established dedicated-server fix as a separate artifact, so client
# rendering and the shared fluid registry remain unchanged in the client jar.
java_home = (Path.home() / 'Library/Application Support/Swift Craft Launcher/runtime/java-runtime-gamma/jre.bundle/Contents/Home')
asm_root = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/libraries/org/ow2/asm')
asm_cp = ":".join(str(asm_root / part / "9.8" / (part + "-9.8.jar")) for part in ["asm", "asm-tree"])
patch_source = ROOT.parents[1] / "servers/cmi-expedition/SteamAgesServerPatch.java"
build_dir = ROOT / "runtime-compat/csa-server-patch"
build_dir.mkdir(parents=True, exist_ok=True)
shutil.copy2(patch_source, build_dir / patch_source.name)
subprocess.run([str(java_home / "bin/javac"), "--release", "17", "-cp", asm_cp, "-d", str(build_dir), str(build_dir / patch_source.name)], check=True)
server_target = ROOT / "downloads/runtime-server" / PATCHED
server_target.parent.mkdir(exist_ok=True)
subprocess.run([str(java_home / "bin/java"), "-cp", str(build_dir) + ":" + asm_cp, "SteamAgesServerPatch", str(target), str(server_target)], check=True)
with zipfile.ZipFile(target) as client, zipfile.ZipFile(server_target) as server:
    server_changed = [name for name in client.namelist() if client.read(name) != server.read(name)]
    assert server_changed == ["dev/celestiacraft/create_steam_ages/commom/register/CSAFluids.class"], server_changed

legacy = MODS / ORIGINAL
if legacy.exists():
    legacy.unlink()
tags = ROOT / "staging/kubejs/server_scripts/expedition/LegacySteamTags.js"
tags.write_text('''// CSA fluid IDs remain registered; Steam Letters handles their boiler input.
ServerEvents.tags("fluid", event => {
    // The old high-temperature steam used the same level 18 as superheated steam.
    event.get("forge:superheated_steam").add("#forge:high_temperature_steam")
})
''')
out = {
    "source": str(backup.relative_to(ROOT)), "sourceSha256": source_hash,
    "patched": str(target.relative_to(ROOT)), "patchedSha256": hashlib.sha256(target.read_bytes()).hexdigest(),
    "changedEntries": changed, "unchangedClasses": len(classes), "unchangedDataAndAssets": len(assets),
    "dedicatedServer": {"file": str(server_target.relative_to(ROOT)), "sha256": hashlib.sha256(server_target.read_bytes()).hexdigest(), "changedEntriesFromClient": server_changed, "patchSource": str((build_dir / patch_source.name).relative_to(ROOT)), "patchSourceSha256": hashlib.sha256(patch_source.read_bytes()).hexdigest(), "scope": "Established two-RenderType-supplier server fix applied after Steam Letters coexistence patch; the source enforces exactly two removals."},
    "disabledMixin": "dev.celestiacraft.create_steam_ages.mixin.BoilerDataMixin",
    "replacementReview": {
        "createHandler overwrite": "Steam Letters supplies the expanded handler, including stored water and drainable steam; allowing CSA to overwrite it would lose these behaviors.",
        "csa$applySteamHeat": "Identical heat-level update is supplied by Steam Letters sl$applySteamHeat.",
        "csa$sampleSteamSupply": "Identical sample accumulation is supplied by Steam Letters sl$sampleSteamSupply.",
        "csa$notifySteamInput and private fields": "Used only by CSA's old handler; Steam Letters handler uses sl$notifySteamInput and its own fields. No other CSA entrypoint references the old interface.",
        "steam heat levels": "Normal steam remains forge:steam level 9. Legacy forge:high_temperature_steam is included in forge:superheated_steam, retaining level 18.",
        "registries and recipes": "All original classes, recipes, tags, fluid types, fluids, buckets, block registrations and assets are byte-identical. Existing fluid stacks retain their registry IDs."
    },
    "verification": "Archive entry comparison and method bytecode review passed; Forge restart and in-game boiler handler audit are performed by root.",
    "rebuild": "python3 releases/upstream-sync-20261029/patch_csa_compat.py"
}
evidence = ROOT / "evidence/csa-steamletters-compat"
evidence.mkdir(exist_ok=True)
(evidence / "patch-manifest.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(out, ensure_ascii=False, indent=2))
