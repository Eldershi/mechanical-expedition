#!/usr/bin/env python3
"""Install complete native smeltery exports in a closed Overworld copy."""

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import io
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory

import nbtlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "world-server" / "migration"))
from audit_block_palettes import AIR, properties, region_chunks
from migrate_quartz_and_peat import read_indices, write_indices
from prepare_region_copy import replace_chunk

TARGET = "modernfoundry:"
LEGACY = "tconstruct:"


def legacy_id(name):
    return LEGACY + name.removeprefix(TARGET)


def plans(exports, catalog):
    regions = defaultdict(lambda: defaultdict(dict))
    controllers = []
    for export in exports:
        manifest = json.loads((export / "transfer.json").read_text())
        for index, row in enumerate(manifest, 1):
            if row["withheld"]:
                raise ValueError(f"Incomplete transfer for {row['controller']}: {row['withheld']}")
            template = nbtlib.load(export / f"smeltery_{index}.nbt")
            if template["DataVersion"] != 3955 or len(template["blocks"]) != row["blocks"]:
                raise ValueError(f"Invalid target template for {row['controller']}")
            controllers.append(row["controller"])
            for block in template["blocks"]:
                xyz = tuple(a + int(b) for a, b in zip(row["origin"], block["pos"], strict=True))
                x, _, z = xyz
                state = template["palette"][block["state"]]
                name = str(state["Name"])
                entity = block.get("nbt")
                target = catalog.get(name, {})
                schema = target.get("properties")
                if (not name.startswith(TARGET) or schema is None
                        or any(v not in schema.get(k, ()) for k, v in properties(state).items())
                        or entity is not None and (not target["block_entity"] or not entity["id"].startswith(TARGET))):
                    raise ValueError(f"Invalid target block or block entity at {xyz}")
                change = regions[x // 512, z // 512][x // 16, z // 16]
                if xyz in change:
                    raise ValueError(f"Overlapping smeltery templates at {xyz}")
                change[xyz] = state, entity
    return regions, controllers


def at_position(entity, xyz):
    result = deepcopy(entity)
    result.update({key: nbtlib.Int(value) for key, value in zip("xyz", xyz, strict=True)})
    return result


def rewrite_chunk(chunk, changes, counts):
    block_entities = chunk.setdefault("block_entities", nbtlib.List[nbtlib.Compound]())
    by_position = {tuple(int(e[k]) for k in "xyz"): e for e in block_entities}
    sections = {int(section["Y"]): section for section in chunk["sections"]}
    touched = defaultdict(list)
    for xyz, change in changes.items():
        touched[xyz[1] // 16].append((xyz, *change))
    changed = False
    for sy, targets in touched.items():
        states = sections[sy]["block_states"]
        palette = list(states["palette"])
        values = read_indices(states, len(palette))
        palette_changed = False
        for xyz, state, payload in targets:
            x, y, z = xyz
            index = (y % 16) * 256 + (z % 16) * 16 + x % 16
            old = palette[values[index]]
            original_id = str(old["Name"])
            target_id = str(state["Name"])
            if original_id not in AIR and (original_id not in (target_id, legacy_id(target_id))
                                          or properties(old) != properties(state)):
                raise ValueError(f"Occupied smeltery position {xyz}: {old.snbt()}")
            existing = by_position.get(xyz)
            if existing is not None:
                if payload is None:
                    raise ValueError(f"Unrelated block entity at {xyz}: {existing['id']}")
                wanted = at_position(payload, xyz)
                if existing == wanted:
                    existing = None
                    wanted = None
                elif (existing["id"] != legacy_id(str(payload["id"]))
                      or original_id != legacy_id(target_id)):
                    raise ValueError(f"Conflicting block entity at {xyz}: {existing['id']}")
            else:
                wanted = at_position(payload, xyz) if payload is not None else None
            if existing is not None:
                block_entities.remove(existing)
            if wanted is not None:
                block_entities.append(wanted)
                counts["block_entities_written"] += 1
                changed = True
            if state != old:
                if state not in palette:
                    palette.append(state)
                values[index] = palette.index(state)
                counts["blocks_written"] += 1
                counts["filled_air" if original_id in AIR else "replaced_legacy"] += 1
                counts[f"source/{original_id}"] += 1
                palette_changed = True
        if palette_changed:
            write_indices(states, palette, values)
            changed = True
    if not changed:
        return False
    chunk.pop("Heightmaps", None)
    chunk.pop("isLightOn", None)
    for section in chunk["sections"]:
        section.pop("SkyLight", None)
        section.pop("BlockLight", None)
    return True


def apply(world, output, exports, catalog):
    regions, controllers = plans(exports, catalog)
    counts = Counter()
    with TemporaryDirectory(dir=output.parent) as temp:
        staging = Path(temp) / "world"
        shutil.copytree(world, staging, ignore=shutil.ignore_patterns("session.lock"))
        for (rx, rz), changes in regions.items():
            rel = Path("region") / f"r.{rx}.{rz}.mca"
            source = world / rel
            original = source.read_bytes()
            updated = None
            missing = set(changes)
            for slot, offset, coords, payload in region_chunks(source, original):
                if coords not in changes:
                    continue
                missing.remove(coords)
                if original[offset + 4] & 128:
                    raise ValueError(f"Cannot write an external smeltery chunk at {coords}")
                chunk = nbtlib.File.parse(io.BytesIO(payload))
                if (int(chunk["xPos"]), int(chunk["zPos"])) != coords:
                    raise ValueError(f"Misplaced smeltery chunk at {coords}")
                if rewrite_chunk(chunk, changes[coords], counts):
                    if updated is None:
                        updated = bytearray(original)
                    replace_chunk(updated, slot, offset, original[slot + 3], chunk)
                    counts["chunks_written"] += 1
            if missing:
                raise ValueError(f"Missing destination chunks in {rel}: {sorted(missing)}")
            if updated is not None:
                (staging / rel).write_bytes(updated)
        staging.rename(output)
    return {"controllers": controllers, "counts": counts}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("world", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("exports", type=Path, nargs="+")
    args = parser.parse_args()
    world, output = args.world.resolve(), args.output.resolve()
    if not world.is_dir() or output.exists() or output.is_relative_to(world):
        parser.error("Pass a closed source world and a new output directory outside it")
    result = apply(world, output, args.exports, json.loads(args.catalog.read_text())["blocks"])
    print(json.dumps(result, indent=2))
