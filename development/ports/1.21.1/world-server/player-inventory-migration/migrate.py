#!/usr/bin/env python3
"""Stage 1.20.1 player inventories and Sophisticated Backpacks for Minecraft 1.21.1."""

import argparse
from collections import Counter
from copy import deepcopy
import json
import os
from pathlib import Path
import runpy
import subprocess
from tempfile import TemporaryDirectory
from uuid import UUID

from nbtlib import Byte, Compound, Float, Int, List, String, load
from nbtlib.nbt import File
from spell_components import spell_components


HERE = Path(__file__).resolve().parent
CREATE = HERE.parent / "create-inventory-migration"
SOURCE_VERSION = 3465
TARGET_VERSION = 3955
STACK_MARKER = "__expedition_stack"
ALIASES = {
    "tconstruct:seared_bricks": "modernfoundry:seared_bricks",
    "tconstruct:seared_faucet": "modernfoundry:seared_faucet",
    "tconstruct:molten_bronze_bucket": "modernfoundry:molten_bronze_bucket",
    "tconstruct:liquid_soul_bucket": "modernfoundry:liquid_soul_bucket",
    "thermal:copper_nugget": "create:copper_nugget",
    "thermal:electrum_ingot": "alltheores:electrum_ingot",
    "thermal:electrum_block": "alltheores:electrum_block",
    "thermal:raw_silver": "alltheores:raw_silver",
    "thermal:lead_ingot": "alltheores:lead_ingot",
    "eidolon:tattered_cloth": "eidolon_repraised:tattered_cloth",
    "eidolon:grape_candy": "eidolon_repraised:grape_candy",
}
BUILDER_DATA = {"Inventory": "inventory", "energy": "energy", "rotation": "structure_rotation", "uuid": "uuid"}
CURIO = "curios:inventory"
MAGIC = "irons_spellbooks:magic_data"
ATTACHMENTS = "neoforge:attachments"
BACKPACK = "sophisticatedbackpacks.dat"


def save(data, path):
    File(data, gzipped=True).save(path)


def datafix(java_home, libraries, work, players, stacks):
    classpath = runpy.run_path(str(CREATE / "migrate.py"))["java_classpath"](libraries)
    task = work / "raw.nbt"
    result = work / "fixed.nbt"
    save({"Players": List[Compound](players), "Stacks": List[Compound](stacks)}, task)
    subprocess.run([java_home / "bin/javac", "--release", "21", "-proc:none", "-cp", classpath, "-d", work,
                    HERE / "PlayerDataFixer.java", CREATE / "LegacyCreateFilters.java"], check=True)
    subprocess.run([java_home / "bin/java", "-Xmx2G", "-cp", os.pathsep.join((str(work), classpath)),
                    "expedition.migration.PlayerDataFixer", task, result], cwd=work, check=True)
    return load(result)


def require_source_version(data, name):
    if data.get("DataVersion") != SOURCE_VERSION:
        raise ValueError(f"{name} is not a Minecraft 1.20.1 save")


def stack_shape(value):
    return isinstance(value, Compound) and isinstance(value.get("id"), String) and "Count" in value


def enchantments(tag):
    for key in ("Enchantments", "StoredEnchantments"):
        for enchantment in tag.get(key, ()):
            yield str(enchantment["id"])


class Migration:
    def __init__(self, registry):
        self.items = set(registry["items"])
        self.enchantments = set(registry["enchantments"])
        if "minecraft:air" not in self.items or "minecraft:protection" not in self.enchantments:
            raise ValueError("Expected real item and enchantment registries from the target server")
        self.requests = []
        self.plans = []
        self.recovery = []
        self.counts = Counter()
        self.missing_items = Counter()
        self.missing_enchantments = Counter()

    def archive(self, owner, path, reason, stack):
        self.recovery.append(Compound({"Source": String(owner), "Path": String(path),
                                       "Reason": String(reason), "Original": deepcopy(stack)}))

    def prepare_tree(self, value, owner, path):
        if stack_shape(value):
            return self.prepare_stack(value, owner, path)
        if isinstance(value, Compound):
            converted = ((key, self.prepare_tree(tag, owner, f"{path}/{key}")) for key, tag in value.items())
            return Compound({key: tag for key, tag in converted if tag is not None})
        if isinstance(value, List):
            converted = (self.prepare_tree(tag, owner, f"{path}[{index}]") for index, tag in enumerate(value))
            return type(value)(tag for tag in converted if tag is not None)
        return value

    def prepare_stack(self, source, owner, path):
        original_id = str(source["id"])
        amount = int(source.get("realCount", source["Count"]))
        if original_id == "minecraft:air" or amount == 0:
            return None
        if amount < 0:
            self.archive(owner, path, "invalid_count", source)
            return None
        self.counts["sourceStacks"] += 1
        self.counts["sourceItems"] += amount
        payload = deepcopy(source)
        old_tag = payload.get("tag", Compound())
        replacement = ALIASES.get(original_id)
        if replacement in self.items and original_id not in self.items and not old_tag and not payload.get("ForgeCaps"):
            payload["id"] = String(replacement)
        if payload["id"] not in self.items and not original_id.startswith("minecraft:"):
            self.archive(owner, path, "item_unavailable", source)
            self.missing_items[original_id] += amount
            return None
        if payload.get("ForgeCaps"):
            self.archive(owner, path, "legacy_item_capability", source)
        payload.pop("ForgeCaps", None)
        slot = payload.pop("Slot", None)
        payload.pop("realCount", None)
        payload["Count"] = Byte(min(amount, 64))
        unsupported = set(enchantments(old_tag)) - self.enchantments
        if unsupported:
            self.archive(owner, path, "enchantment_unavailable", source)
            self.missing_enchantments.update(unsupported)
            for key in ("Enchantments", "StoredEnchantments"):
                if key in old_tag:
                    old_tag[key] = List[Compound](e for e in old_tag[key] if e["id"] in self.enchantments)

        try:
            followup = dict(spell_components(old_tag))
        except ValueError:
            self.archive(owner, path, "unverified_spell_payload", source)
            followup = {}
        for key in followup:
            old_tag.pop(key)
        block_entity = old_tag.get("BlockEntityTag", Compound())
        if "Items" in block_entity:
            followup["minecraft:container"] = self.prepare_tree(
                block_entity.pop("Items"), owner, f"{path}/tag/BlockEntityTag/Items")
        for legacy_key, component in (("ChargedProjectiles", "minecraft:charged_projectiles"),
                                      ("Items", "minecraft:bundle_contents")):
            if legacy_key in old_tag and (legacy_key != "Items" or original_id == "minecraft:bundle"):
                followup[component] = self.prepare_tree(old_tag.pop(legacy_key), owner, f"{path}/tag/{legacy_key}")
        if original_id.startswith("sophisticatedbackpacks:"):
            for key in ("craftingInventory", "inventory", "filters"):
                if key in old_tag:
                    followup[key] = self.prepare_tree(old_tag.pop(key), owner, f"{path}/tag/{key}")
            old_tag.pop("renderInfo", None)  # Recomputed by the backpack from its actual upgrades.
        if original_id == "mbtool:mbtool":
            for old, new in BUILDER_DATA.items():
                if old in old_tag:
                    followup[f"mbtool:{new}"] = self.prepare_tree(old_tag.pop(old), owner, f"{path}/tag/{old}")
            if "recipe" in old_tag:
                # A compiled structure index is not portable between recipe sets.
                self.archive(owner, path, "unverified_structure_selection", source)
                old_tag.pop("recipe")
        if original_id.startswith("create_jetpack:") and "Air" in old_tag:
            followup["create:banktank_air"] = Int(old_tag.pop("Air"))
        if "affix_data" in old_tag or "gem" in old_tag:
            self.archive(owner, path, "unverified_legacy_affixes", source)
        index = len(self.requests)
        self.requests.append(payload)
        self.plans.append((owner, path, source, slot, amount, followup))
        return Compound({STACK_MARKER: Int(index)})

    def resolve(self, value, fixed):
        if isinstance(value, Compound):
            if STACK_MARKER in value:
                return self.resolve_stack(int(value[STACK_MARKER]), fixed)
            converted = ((key, self.resolve(tag, fixed)) for key, tag in value.items())
            return Compound({key: tag for key, tag in converted if tag is not None})
        if isinstance(value, List):
            converted = (self.resolve(tag, fixed) for tag in value)
            return type(value)(tag for tag in converted if tag is not None)
        return value

    def resolve_stack(self, index, fixed):
        owner, path, source, slot, amount, followup = self.plans[index]
        stack = deepcopy(fixed[index])
        if stack.get("id") not in self.items or "count" not in stack or "Count" in stack or "tag" in stack:
            self.archive(owner, path, "invalid_datafixer_result", source)
            self.missing_items[str(source["id"])] += amount
            return None
        if slot is not None:
            stack["Slot"] = slot
        stack["count"] = Int(amount)
        if followup:
            components = stack.setdefault("components", Compound())
            for key, tag in followup.items():
                converted = self.resolve(tag, fixed)
                if key == "minecraft:container":
                    contents = List[Compound]()
                    for item in converted:
                        position = Int(item.pop("Slot"))
                        contents.append(Compound({"slot": position, "item": item}))
                    components[key] = contents
                elif ":" in key:
                    components[key] = converted
                else:
                    components.setdefault("minecraft:custom_data", Compound())[key] = converted
        self.counts["convertedStacks"] += 1
        self.counts["convertedItems"] += amount
        return stack


def stage(source, target_registry, java_home, libraries, work):
    transfer = Migration(target_registry)
    players, inventories, original_states = [], [], []
    source_players = sorted((source / "playerdata").glob("*.dat"))
    if not source_players:
        raise ValueError("No player data available")
    for ordinal, file in enumerate(source_players, start=1):
        identifier = UUID(file.stem)
        owner = f"player-{ordinal}"
        data = load(file)
        require_source_version(data, owner)
        persisted_uuid = data.get("UUID")
        if persisted_uuid is None or len(persisted_uuid) != 4:
            raise ValueError(f"{owner} has no valid UUID")
        encoded_uuid = int.from_bytes(b"".join(int(value).to_bytes(4, "big", signed=True)
                                                for value in persisted_uuid), "big")
        if identifier.int != encoded_uuid:
            raise ValueError(f"{owner} has a mismatched player identity")
        recorded = Compound()
        inventories.append(recorded)
        for key in ("Inventory", "EnderItems"):
            recorded[key] = transfer.prepare_tree(data.pop(key, List[Compound]()), owner, key)
        old_capabilities = data.pop("ForgeCaps", Compound())
        attachments = data.setdefault(ATTACHMENTS, Compound())
        if CURIO in old_capabilities:
            recorded[CURIO] = transfer.prepare_tree(old_capabilities[CURIO], owner, CURIO)
        magic = data.pop(MAGIC, None)
        if magic is not None:
            attachments[MAGIC] = deepcopy(magic)
            attachments[MAGIC]["mana"] = Float(magic.get("mana", 0))
        original = Compound({"Source": String(owner), "ForgeCaps": old_capabilities})
        if magic is not None:
            original[MAGIC] = magic
        original_states.append(original)
        players.append(Compound(data))

    bag_path = source / "data" / BACKPACK
    backpacks = load(bag_path)
    require_source_version(backpacks, "backpack storage")
    bags = backpacks["data"]["backpackContents"]
    backpacks["data"]["backpackContents"] = transfer.prepare_tree(bags, "backpack-storage", "backpackContents")
    backpacks["DataVersion"] = Int(TARGET_VERSION)
    result = datafix(java_home, libraries, work, players, transfer.requests)
    fixed = result["Stacks"]

    output = work / "output"
    output.mkdir(mode=0o700)
    player_dir = output / "playerdata"
    bag_dir = output / "data"
    player_dir.mkdir()
    bag_dir.mkdir()
    for file, player, inventory in zip(source_players, result["Players"], inventories, strict=True):
        for key in ("Inventory", "EnderItems"):
            player[key] = transfer.resolve(inventory[key], fixed)
        if CURIO in inventory:
            player[ATTACHMENTS][CURIO] = transfer.resolve(inventory[CURIO], fixed)
        save(player, player_dir / file.name)
    backpacks["data"]["backpackContents"] = transfer.resolve(backpacks["data"]["backpackContents"], fixed)
    save(backpacks, bag_dir / BACKPACK)
    save({"Stacks": List[Compound](transfer.recovery), "PlayerCapabilities": List[Compound](original_states)},
         output / "legacy-recovery.nbt")
    summary = {"players": len(players), "backpackEntries": len(bags), "counts": dict(transfer.counts),
               "missingItems": dict(transfer.missing_items), "missingEnchantments": dict(transfer.missing_enchantments),
               "recoveryReasons": dict(Counter(entry["Reason"] for entry in transfer.recovery))}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return output, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "target-registry", "java-home", "libraries", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or source == output or source in output.parents:
        parser.error("Use a new output directory outside the source archive")
    output.parent.mkdir(parents=True, exist_ok=True)
    registry = json.loads(args.target_registry.read_text())
    with TemporaryDirectory(prefix="player-migration-", dir=output.parent) as temporary:
        work = Path(temporary)
        result, summary = stage(source, registry, args.java_home.resolve(), args.libraries.resolve(), work)
        if output.exists():
            raise FileExistsError(output)
        result.rename(output)
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
