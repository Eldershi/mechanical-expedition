#!/usr/bin/env python3
"""Build/apply the isolated Tectonic preview, using only Python's standard library.

Audit: python3 apply_preview.py --audit-source clients/cmi-expedition/instance
Apply: python3 apply_preview.py --instance clients/cmi-expedition/tectonic-preview/instance
Application is refused outside the preview tree, or after a save has been created.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ALLOWED = (REPO / "clients/cmi-expedition/tectonic-preview").resolve()
SCOPE = {"geophilic", "wythers", "biomesoplenty", "biomeswevegone", "regions_unexplored", "terralith"}
REGISTRY = re.compile(r"^data/([^/]+)/(worldgen/(?:placed_feature|configured_feature|biome)|dimension_type)/(.+)\.json$")
EXCLUDED = re.compile(r"(?:^|[/_])(?:shrub|shrubs|bush|bushes|fallen|stump|stumps|logs|log|mushroom|mushrooms|bioshroom|bioshrooms|fungus|fungi|cactus|cacti|bamboo)(?:$|[/_])")
VANILLA_TREES = {
    "oak", "oak_bees_0002", "oak_bees_002", "oak_bees_005", "oak_checked", "dark_oak", "dark_oak_checked",
    "birch", "birch_bees_0002", "birch_bees_002", "birch_bees_005", "birch_checked", "birch_tall", "birch_tall_checked",
    "fancy_oak", "fancy_oak_bees_0002", "fancy_oak_bees_002", "fancy_oak_bees_005", "fancy_oak_checked",
    "spruce", "spruce_checked", "pine", "pine_checked", "mega_spruce", "mega_spruce_checked", "mega_pine", "mega_pine_checked",
    "acacia", "acacia_checked", "jungle_tree", "jungle_tree_checked", "mega_jungle_tree", "mega_jungle_tree_checked",
    "jungle_tree_no_vine", "jungle_tree_no_vine_checked", "jungle_bush", "mangrove", "tall_mangrove", "cherry", "cherry_bees_005",
}
TREE_TYPES = {
    "minecraft:tree", "ohthetreesyoullgrow:tree", "ohthetreesyoullgrow:tree_from_nbt_v1",
    "biomesoplenty:basic_tree", "biomesoplenty:big_tree", "biomesoplenty:twiglet_tree", "biomesoplenty:taiga_tree",
    "biomesoplenty:poplar_tree", "biomesoplenty:redwood_tree", "biomesoplenty:cypress_tree",
    "biomesoplenty:palm_tree", "biomesoplenty:mahogany_tree",
    "regions_unexplored:aspen_tree", "regions_unexplored:stripped_pine_tree", "regions_unexplored:sakura_tree",
    "regions_unexplored:larch_tree", "regions_unexplored:pine_tree", "regions_unexplored:maple_tree",
    "regions_unexplored:palm_tree", "regions_unexplored:ashen_tree", "regions_unexplored:blackwood_tree",
    "regions_unexplored:cobalt_tree", "regions_unexplored:cypress_tree", "regions_unexplored:dead_tree",
    "regions_unexplored:eucalyptus_tree", "regions_unexplored:giant_cypress_tree", "regions_unexplored:super_redwood_tree",
    "regions_unexplored:small_joshua_tree", "regions_unexplored:kapok_tree", "regions_unexplored:large_joshua_tree",
    "regions_unexplored:large_socotra_tree", "regions_unexplored:lush_pine_tree", "regions_unexplored:medium_joshua_tree",
    "regions_unexplored:mega_baobab_tree", "regions_unexplored:redwood_tree", "regions_unexplored:small_eucalyptus_tree",
    "regions_unexplored:small_oak_tree", "regions_unexplored:small_socotra_tree", "regions_unexplored:ultra_baobab_tree",
    "regions_unexplored:ultra_redwood_tree",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def encoded(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()


def atomic_write(path: Path, data: bytes):
    """Break hard links as well as replacing complete files atomically."""
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    with tempfile.NamedTemporaryFile(prefix=f".{path.name}.preview-", dir=path.parent, delete=False) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(data)
    try:
        tmp_path.chmod(mode)
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)


def load_registry(instance: Path):
    registries = defaultdict(dict)
    sources = defaultdict(list)
    jar_hashes = []
    excluded_biomes = set()
    for jar in sorted((instance / "mods").glob("*.jar")):
        with zipfile.ZipFile(jar) as archive:
            for tag in ("is_nether", "is_end"):
                path = f"data/minecraft/tags/worldgen/biome/{tag}.json"
                if path in archive.namelist():
                    for value in json.loads(archive.read(path)).get("values", []):
                        value = value.get("id") if isinstance(value, dict) else value
                        if isinstance(value, str) and not value.startswith("#"):
                            excluded_biomes.add(value)
            relevant = [n for n in archive.namelist() if REGISTRY.match(n)]
            if not relevant:
                continue
            # Only hash JARs whose worldgen is used by the vegetation scope or height overrides.
            if any(REGISTRY.match(n).group(1) in SCOPE for n in relevant):
                jar_hashes.append({"file": jar.name, "sha256": sha(jar.read_bytes())})
            for name in relevant:
                match = REGISTRY.match(name)
                namespace, registry, resource = match.groups()
                key = f"{namespace}:{resource}"
                try:
                    obj = json.loads(archive.read(name))
                except (ValueError, UnicodeDecodeError):
                    continue
                registries[registry][key] = obj
                sources[(registry, key)].append(f"mods/{jar.name}!/{name}")
    for path in sorted((instance / "kubejs/data").rglob("*.json")):
        name = "data/" + path.relative_to(instance / "kubejs/data").as_posix()
        match = REGISTRY.match(name)
        if match:
            namespace, registry, resource = match.groups()
            key = f"{namespace}:{resource}"
            registries[registry][key] = json.loads(path.read_bytes())
            sources[(registry, key)].append(path.relative_to(instance).as_posix())
    registries["excluded_biomes"] = {key: True for key in excluded_biomes}
    return registries, sources, jar_hashes


def feature_types(value, kind, registries, seen=()):
    """Resolve selector endpoints. Unresolved/mixed resources are explicit audit failures.

    Strings in configured selectors refer to placed features, while a placed feature's
    `feature` string refers to a configured feature. Inline holders follow the same rule.
    """
    if isinstance(value, str):
        if ":" not in value:
            value = "minecraft:" + value
        marker = (kind, value)
        if marker in seen:
            return {"cycle:" + value}
        obj = registries[kind].get(value)
        if obj is None:
            if value.startswith("minecraft:") and value.partition(":")[2] in VANILLA_TREES:
                return {"tree"}
            return {"unresolved:" + value}
        return feature_types(obj, kind, registries, seen + (marker,))
    if not isinstance(value, dict):
        return {"invalid-holder"}
    if kind == "worldgen/placed_feature":
        return feature_types(value.get("feature"), "worldgen/configured_feature", registries, seen)
    typ = value.get("type", "")
    if ":" not in typ:
        typ = "minecraft:" + typ
    if typ in TREE_TYPES:
        return {"tree"}
    config = value.get("config", {})
    children = []
    if typ == "minecraft:random_selector":
        children = [item["feature"] for item in config.get("features", [])]
        children += [config["default"]] if "default" in config else []
    elif typ == "minecraft:simple_random_selector":
        children = config.get("features", [])
    elif typ == "minecraft:random_boolean_selector":
        children = [config.get("feature_true"), config.get("feature_false")]
    if children:
        return set().union(*(feature_types(child, "worldgen/placed_feature", registries, seen) for child in children))
    return {"other:" + typ}


def resource_path(registry: str, key: str) -> str:
    namespace, _, resource = key.partition(":")
    return f"kubejs/data/{namespace}/{registry}/{resource}.json"


def placed_dependencies(value, kind, registries, seen=()):
    """Collect referenced placed-feature keys through selectors, including inline ones."""
    if isinstance(value, str):
        value = value if ":" in value else "minecraft:" + value
        if (kind, value) in seen:
            return set()
        own = {value} if kind == "worldgen/placed_feature" else set()
        return own | placed_dependencies(registries[kind].get(value), kind, registries, seen + ((kind, value),))
    if not isinstance(value, dict):
        return set()
    if kind == "worldgen/placed_feature":
        return placed_dependencies(value.get("feature"), "worldgen/configured_feature", registries, seen)
    typ = value.get("type", "").split(":")[-1]
    config = value.get("config", {})
    children = []
    if typ == "random_selector":
        children = [item["feature"] for item in config.get("features", [])]
        children += [config["default"]] if "default" in config else []
    elif typ == "simple_random_selector":
        children = config.get("features", [])
    elif typ == "random_boolean_selector":
        children = [config.get("feature_true"), config.get("feature_false")]
    return set().union(*(placed_dependencies(child, "worldgen/placed_feature", registries, seen) for child in children)) if children else set()


def make_plan(instance: Path):
    registries, sources, jar_hashes = load_registry(instance)
    changes = {}
    tectonic_path = instance / "config/tectonic.json"
    config = json.loads(tectonic_path.read_bytes())
    old_tectonic = copy.deepcopy(config)
    config["continents"].update(continents_scale=0.17, erosion_scale=0.30, ridge_scale=0.25)
    config["biomes"].update(temperature_scale=0.28, vegetation_scale=0.28, vegetation_offset=-0.10)
    config["global_terrain"].update(min_y=-64, max_y=640, elevation_boost=1.0, vertical_scale=1.125)
    changes["config/tectonic.json"] = encoded(config)
    tb_path = instance / "config/terrablender.toml"
    tb_old = tb_path.read_text()
    tb_new, count = re.subn(r"(?m)^(\s*overworld_region_size\s*=\s*)[2-6](\s*)$", r"\g<1>3\2", tb_old)
    if count != 1:
        raise ValueError("Expected exactly one TerraBlender overworld_region_size setting")
    changes["config/terrablender.toml"] = tb_new.encode()
    noise = copy.deepcopy(registries["worldgen/noise_settings"].get("minecraft:overworld"))
    # load_registry intentionally restricts biome/feature registries, so load the exact KubeJS source.
    noise_path = instance / "kubejs/data/minecraft/worldgen/noise_settings/overworld.json"
    if not noise_path.exists():
        raise ValueError("Expected the pack's existing KubeJS overworld noise source")
    noise = json.loads(noise_path.read_bytes())
    noise_before = copy.deepcopy(noise["noise"])
    noise["noise"].update(min_y=-64, height=704)
    changes["kubejs/data/minecraft/worldgen/noise_settings/overworld.json"] = encoded(noise)
    dim_key = ("dimension_type", "minecraft:overworld")
    dimension = copy.deepcopy(registries[dim_key[0]].get(dim_key[1]))
    if not isinstance(dimension, dict):
        raise ValueError("No existing overworld dimension_type found")
    dim_before = {k: dimension[k] for k in ("min_y", "height", "logical_height")}
    dimension.update(min_y=-64, height=704, logical_height=704)
    changes["kubejs/data/minecraft/dimension_type/overworld.json"] = encoded(dimension)

    biome_users = defaultdict(list)
    for biome, obj in registries["worldgen/biome"].items():
        if biome.partition(":")[0] not in SCOPE | {"minecraft"}:
            continue
        if biome in registries["excluded_biomes"]:
            continue
        # Surface vegetation stage only. Do not alter underground/nether flora.
        features = obj.get("features", [])
        if len(features) > 9:
            for ref in features[9]:
                if isinstance(ref, str):
                    biome_users[ref if ":" in ref else "minecraft:" + ref].append(biome)
    selected, skipped = [], []
    for key, users in sorted(biome_users.items()):
        if key.partition(":")[0] not in SCOPE:
            continue
        obj = registries["worldgen/placed_feature"].get(key)
        if obj is None:
            skipped.append({"feature": key, "reason": "missing placed feature", "biomes": users})
            continue
        types = feature_types(obj, "worldgen/placed_feature", registries)
        if EXCLUDED.search(key.partition(":")[2]):
            if types == {"tree"}:
                skipped.append({"feature": key, "reason": "preserve shrubs/logs/special vegetation by name", "types": sorted(types), "biomes": users})
            continue
        if types != {"tree"}:
            if "tree" in types or re.search(r"(?:tree|forest|pine|spruce|oak|birch|redwood|cypress|willow)", key):
                skipped.append({"feature": key, "reason": "mixed, non-tree or unresolved endpoint; preserve", "types": sorted(types), "biomes": users})
            continue
        # The biome directly calls this outer feature. Only thin this layer; embedded
        # single-tree variants are preserved, preventing multiplicative thinning.
        modified = copy.deepcopy(obj)
        modified.setdefault("placement", []).append({"type": "minecraft:rarity_filter", "chance": 2})
        rel = resource_path("worldgen/placed_feature", key)
        changes[rel] = encoded(modified)
        selected.append({"feature": key, "source": sources[("worldgen/placed_feature", key)][-1],
                         "biomes": sorted(users), "original_placement": obj.get("placement", []),
                         "added_modifier": {"type": "minecraft:rarity_filter", "chance": 2},
                         "expected_candidate_retention": 0.5})
    if len(selected) < 100:
        raise ValueError(f"Only {len(selected)} validated tree roots: refusing an unexpectedly narrow vegetation patch")
    counts = dict(Counter(item["feature"].partition(":")[0] for item in selected))
    if not SCOPE <= counts.keys():
        raise ValueError(f"Some intended vegetation namespaces have no validated tree roots: {counts}")
    selected_ids = {item["feature"] for item in selected}
    overlaps = {}
    for key in selected_ids:
        descendants = placed_dependencies(registries["worldgen/placed_feature"][key], "worldgen/placed_feature", registries) & selected_ids
        if descendants:
            overlaps[key] = sorted(descendants)
    if overlaps:
        raise ValueError(f"Selected tree parent/child overlap would thin twice: {overlaps}")
    report = {
        "profile": "tectonic-compact-open-epic-v1", "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source_instance": str(instance), "scope": "brand-new isolated client save only",
        "tectonic_before": old_tectonic, "tectonic_after": config,
        "terrablender_overworld_region_size": {"before": re.search(r"overworld_region_size\s*=\s*(\d+)", tb_old).group(1), "after": 3},
        "height": {"noise_before": noise_before, "dimension_before": dim_before,
                   "noise_after": noise["noise"], "dimension_after": {k: dimension[k] for k in ("min_y", "height", "logical_height")},
                   "dimension_sources": sources[dim_key],
                   "runtime_verification_required": "Actual dimension minY=-64, height=704; generator noise minY=-64, height=704. Also verify tectonic built-in datapack enabled."},
        "vegetation": {"method": "Append chance=2 rarity_filter after all existing placements on validated direct biome vegetation roots; each candidate position independently survives 50%.",
                       "density_limit": "This changes attempts, not a measured promise of 50% fewer final trees or canopy. A few tree-type mixes contain low bushes; separately placed shrubs/logs/flowers/mushrooms are excluded. All custom materials remain registered.",
                       "selection": "Surface vegetation stage 9, allowed namespace, recursive selector endpoints all standing-tree types, explicit name exclusions.",
                       "selected_counts": counts, "selected": selected, "skipped_review": skipped},
        "source_jars": jar_hashes,
        "planned_files": [{"path": rel, "existed": (instance / rel).exists(), "before_sha256": sha((instance / rel).read_bytes()) if (instance / rel).exists() else None,
                           "after_sha256": sha(data)} for rel, data in sorted(changes.items())],
        "load_order_note": "KubeJS data overrides mod JAR resources in this pack. A later file datapack may override these; query live registries after save startup. Never copy a two-entry pack list and assume omitted Forge packs cannot be appended.",
        "validation": {"all_changed_json_parse": True, "height_multiple_of_16": 704 % 16 == 0,
                       "dimension_noise_height_match": True, "tree_roots_have_one_appended_filter": True,
                       "selected_parent_child_overlap": overlaps,
                       "no_existing_world_changes": True, "no_mod_jar_changes": True},
    }
    for rel, data in changes.items():
        if rel.endswith(".json"):
            json.loads(data)
    return changes, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    exclusive = parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument("--instance", type=Path, help="Apply to a new independent instance under the tectonic-preview tree")
    exclusive.add_argument("--audit-source", type=Path, help="Read-only audit of source instance; writes audit only beside this script")
    args = parser.parse_args()
    instance = (args.instance or args.audit_source).resolve()
    if not instance.is_dir():
        parser.error("Instance must already exist")
    if args.instance:
        if instance == ALLOWED or ALLOWED not in instance.parents:
            parser.error(f"Application is allowed only to an instance beneath {ALLOWED}")
        if list((instance / "saves").glob("*/level.dat")):
            parser.error("Apply before creating any world: existing level.dat found")
        marker = instance / ".tectonic-preview-configuration.json"
        if marker.exists():
            parser.error("Preview configuration already applied; refusing to thin a second time")
    changes, report = make_plan(instance)
    if args.audit_source:
        report["mode"] = "read-only-audit"
        output = HERE / "static-audit.json"
        output.write_bytes(encoded(report))
    else:
        # Prepare all output and static validation before any mutation, then back up
        # every existing target. Source files outside the isolated instance are untouched.
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup = instance / ".tectonic-preview-backups" / timestamp
        for rel in changes:
            target = instance / rel
            if instance not in target.resolve().parents:
                raise ValueError(f"Write target escapes independent instance: {target}")
        if instance not in backup.resolve().parents:
            raise ValueError("Backup path escapes independent instance")
        for rel in changes:
            source = instance / rel
            if source.exists():
                target = backup / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
        report.update(mode="applied", backup_directory=str(backup))
        for rel, data in changes.items():
            target = instance / rel
            # Resolve each write, including pre-existing directory symlinks, against
            # the permitted isolated instance before writing anything through it.
            if instance not in target.resolve().parents:
                raise ValueError(f"Write target escapes independent instance: {target}")
            target.parent.mkdir(parents=True, exist_ok=True)
            atomic_write(target, data)
        output = instance / ".tectonic-preview-configuration.json"
        atomic_write(output, encoded(report))
    print(json.dumps({"mode": report["mode"], "manifest": str(output), "changed_files": len(changes),
                      "tree_roots": report["vegetation"]["selected_counts"], "min_y": -64, "height": 704, "max_y": 640}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
