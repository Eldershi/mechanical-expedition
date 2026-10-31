#!/usr/bin/env python3
"""Add the untouched vanilla netherite crafting route to the parallel catalog."""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
RELEASE = Path(__file__).resolve().parent
CATALOG_REL = Path("kubejs/config/expedition-selected-native-recipes.json")
SOURCE_JAR = (Path.home() / 'Library/Application Support/Swift Craft Launcher/meta/versions/1.20.1/1.20.1.jar')
SOURCE_ENTRY = "data/minecraft/recipes/netherite_ingot.json"
EXPECTED_SOURCE_SHA = "dd344c8e4561d527d7e9a47daa674b3eef50961bbe4c5154c9661d8682113303"
NATIVE_ID = "minecraft:netherite_ingot"
PARALLEL_ID = "expedition:selected_native/minecraft/netherite_ingot"
TARGET_ROOTS = [
    Path("servers/cmi-expedition/deployment"),
    Path("servers/cmi-expedition/instance"),
    Path("clients/cmi-expedition/overlay"),
]
ACTIVE_CLIENT = (Path.home() / 'Library/Application Support/Swift Craft Launcher/profiles/机械远征-CMI-迁移测试')


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def render(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> None:
    with zipfile.ZipFile(SOURCE_JAR) as archive:
        source_bytes = archive.read(SOURCE_ENTRY)
    assert sha256(source_bytes) == EXPECTED_SOURCE_SHA, "Unexpected vanilla source JSON"
    recipe_json = json.loads(source_bytes)
    assert recipe_json["type"] == "minecraft:crafting_shapeless"
    assert recipe_json["ingredients"] == (
        [{"item": "minecraft:netherite_scrap"}] * 4
        + [{"item": "minecraft:gold_ingot"}] * 4
    )
    assert recipe_json["result"] == {"item": NATIVE_ID}

    row = {
        "nativeId": NATIVE_ID,
        "json": recipe_json,
        "outputs": [NATIVE_ID],
        "source": SOURCE_JAR.name,
        "sourceEntry": SOURCE_ENTRY,
        "sourceJsonSha256": EXPECTED_SOURCE_SHA,
        "id": PARALLEL_ID,
        "selections": ["下界合金锭｜恢复原版工作台配方"],
    }

    prepared = []
    baseline_bytes = None
    for root in TARGET_ROOTS:
        rel = root / CATALOG_REL
        target = PROJECT / rel
        backup = RELEASE / "backups/project-before" / rel
        original = backup.read_bytes() if backup.exists() else target.read_bytes()
        if baseline_bytes is None:
            baseline_bytes = original
        assert original == baseline_bytes, f"Catalog baselines differ: {target}"
        baseline = json.loads(original)
        assert original == render(baseline), "Catalog has unexpected formatting"
        assert baseline["selectionCount"] == 239
        assert len(baseline["recipes"]) == 2472
        assert all(item["nativeId"] != NATIVE_ID for item in baseline["recipes"])
        assert all(item["id"] != PARALLEL_ID for item in baseline["recipes"])

        updated = dict(baseline)
        updated["selectionCount"] = 240
        updated["recipes"] = baseline["recipes"] + [row]
        new_bytes = render(updated)

        # Verify the update only adds one recipe and increments the selection count.
        reread = json.loads(new_bytes)
        assert reread["recipes"][:-1] == baseline["recipes"]
        assert reread["recipes"][-1] == row
        assert len(reread["recipes"]) == 2473
        restored = dict(reread)
        restored["selectionCount"] = baseline["selectionCount"]
        restored["recipes"] = reread["recipes"][:-1]
        assert restored == baseline
        assert target.read_bytes() in (original, new_bytes), f"Target changed since backup: {target}"
        prepared.append((rel, target, backup, original, new_bytes))

    # All preflight checks complete before any target is changed.
    for rel, target, backup, original, new_bytes in prepared:
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(original)
        target.write_bytes(new_bytes)
        assert target.read_bytes() == new_bytes

    payload = RELEASE / "payload" / CATALOG_REL
    payload.parent.mkdir(parents=True, exist_ok=True)
    payload.write_bytes(prepared[0][4])
    source_copy = RELEASE / "evidence/vanilla-netherite-ingot.json"
    source_copy.parent.mkdir(parents=True, exist_ok=True)
    source_copy.write_bytes(source_bytes)

    old_sha = sha256(prepared[0][3])
    new_sha = sha256(prepared[0][4])
    active_catalog = ACTIVE_CLIENT / CATALOG_REL
    active_sha = sha256(active_catalog.read_bytes()) if active_catalog.exists() else None
    manifest = {
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "operation": "parallel_restore_vanilla_netherite_ingot_crafting",
        "nativeId": NATIVE_ID,
        "parallelId": PARALLEL_ID,
        "sourceJar": str(SOURCE_JAR),
        "sourceEntry": SOURCE_ENTRY,
        "sourceJsonSha256": EXPECTED_SOURCE_SHA,
        "oldCatalogSha256": old_sha,
        "newCatalogSha256": new_sha,
        "selectionCountBefore": 239,
        "selectionCountAfter": 240,
        "recipeCountBefore": 2472,
        "recipeCountAfter": 2473,
        "verification": {
            "vanillaSourceHashMatched": True,
            "vanillaIngredientsFourScrapsFourGold": True,
            "addedExactlyOneRecipe": True,
            "allExistingRecipeRowsUnchanged": True,
            "allOtherCatalogFieldsUnchanged": True,
            "updatedWorkspaceTargetsIdentical": True,
        },
        "workspaceTargets": [
            {
                "path": str(target),
                "backup": str(backup),
                "beforeSha256": sha256(original),
                "afterSha256": sha256(new_bytes),
            }
            for _, target, backup, original, new_bytes in prepared
        ],
        "payload": str(payload),
        "activeClientInstall": {
            "status": "pending",
            "source": str(payload),
            "destination": str(active_catalog),
            "observedDestinationSha256": active_sha,
            "expectedBeforeSha256": old_sha,
            "expectedAfterSha256": new_sha,
            "backupDestination": str(
                RELEASE / "backups/active-client-before" / CATALOG_REL
            ),
        },
        "onlineDeployment": {"status": "pending"},
    }
    (RELEASE / "manifest.json").write_bytes(render(manifest))
    print(json.dumps({"payload": str(payload), "manifest": str(RELEASE / "manifest.json"),
                      "oldSha256": old_sha, "newSha256": new_sha,
                      "workspaceTargetsUpdated": len(prepared),
                      "activeClientModified": False}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
