#!/usr/bin/env python3
"""Export smeltery block layouts and typed payloads from a 1.20.1 region copy."""

import argparse
from collections import Counter
from copy import deepcopy
import gzip
from io import BytesIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import zlib
from zipfile import ZipFile

from nbtlib import Byte, Compound, File, Int, IntArray, List, String


LEGACY = "tconstruct:"
THERMAL = {"thermal", "thermal_extra", "thermalconstruct"}
DECOMPRESS = {1: gzip.decompress, 2: zlib.decompress, 3: lambda data: data}
BLOCK_ENTITIES = {
    "basin", "chute", "drain", "faucet", "smeltery", "smeltery_component", "table", "tank",
}


def chunks(path):
    with path.open("rb") as region:
        header = region.read(8192)
        if not header:
            return
        if len(header) != 8192:
            raise ValueError("Incomplete Anvil region header")
        for index in range(1024):
            entry = header[index * 4:index * 4 + 4]
            sector = int.from_bytes(entry[:3], "big")
            if not sector:
                continue
            region.seek(sector * 4096)
            length = int.from_bytes(region.read(4), "big")
            if sector < 2 or not 1 <= length <= entry[3] * 4096 - 4:
                raise ValueError(f"Invalid chunk allocation at index {index}")
            method = region.read(1)[0]
            if method not in DECOMPRESS:
                raise ValueError(f"Unsupported Anvil compression {method} at index {index}")
            payload = region.read(length - 1)
            if len(payload) != length - 1:
                raise ValueError(f"Truncated chunk at index {index}")
            yield File.parse(BytesIO(DECOMPRESS[method](payload)))


def offset(value):
    if isinstance(value, Compound) and set(value) == {"X", "Y", "Z"}:
        return IntArray([value[axis] for axis in "XYZ"])
    if isinstance(value, IntArray) and len(value) == 3:
        return value
    raise ValueError(f"Unsupported block offset {value!r}")


def position(block_entity):
    return tuple(int(block_entity[axis]) for axis in "xyz")


def renamed(value, namespace):
    return String(f"{namespace}:{value.removeprefix(LEGACY)}") if value.startswith(LEGACY) else value


def fluid(stack, namespace, excluded, withheld):
    if "FluidName" not in stack:
        return stack
    unexpected = stack.keys() - {"FluidName", "Amount", "Tag"}
    if unexpected:
        raise ValueError(f"Unsupported legacy fluid data for {stack['FluidName']}")
    resource = stack["FluidName"]
    amount = int(stack["Amount"])
    if resource.split(":", 1)[0] in THERMAL or resource in excluded:
        withheld["fluid", str(resource)] += amount
        return Compound()
    result = Compound({"id": renamed(resource, namespace), "amount": Int(amount)})
    if stack.get("Tag"):
        if resource != "tconstruct:potion" or set(stack["Tag"]) != {"Potion"}:
            raise ValueError(f"Legacy fluid components need explicit conversion for {resource}")
        result["components"] = Compound({"minecraft:custom_data": deepcopy(stack["Tag"])})
    return result


def item(stack, namespace, excluded, withheld):
    if stack["id"] in excluded or stack["id"].split(":", 1)[0] in THERMAL:
        withheld["item", str(stack["id"])] += int(stack.get("Count", stack.get("count", 1)))
        return None
    if "Count" in stack:
        if stack.get("tag") or stack.get("ForgeCaps"):
            raise ValueError(f"Legacy item components need explicit conversion for {stack['id']}")
        stack["count"] = Int(stack.pop("Count"))
        stack.pop("tag", None)
        stack.pop("ForgeCaps", None)
    stack["id"] = renamed(stack["id"], namespace)
    return stack


def convert(entity, namespace, excluded, withheld):
    result = deepcopy(entity)
    kind = str(result["id"]).removeprefix(LEGACY)
    if kind not in BLOCK_ENTITIES:
        raise ValueError(f"Unsupported smeltery block entity {result['id']}")
    result["id"] = renamed(result["id"], namespace)
    for key in ("x", "y", "z", "keepPacked", "ForgeCaps"):
        if key == "ForgeCaps" and result.get(key):
            raise ValueError(f"Non-empty Forge capabilities at {position(entity)}")
        result.pop(key, None)
    for key in ("masterBlock", "texture", "recipe"):
        if key in result:
            result[key] = renamed(result[key], namespace)
    for key in ("masterOffset", "last_fuel"):
        if key in result:
            result[key] = offset(result[key])
    structure = result.get("multiblock")
    if structure:
        for key in ("min", "max", "insideCheck"):
            if key in structure:
                structure[key] = offset(structure[key])
        for key in ("tanks", "extra"):
            if key in structure:
                positions = (offset(value) for value in structure[key])
                if key == "tanks" and namespace == "modernfoundry":
                    structure[key] = List[Compound](Compound({"pos": value}) for value in positions)
                else:
                    structure[key] = List[IntArray](positions)
    tank = result.get("tank")
    if tank:
        if "fluids" in tank:
            converted = (fluid(value, namespace, excluded, withheld) for value in tank["fluids"])
            tank["fluids"] = List[Compound](value for value in converted if value)
        elif "fluid" in tank:
            replacement = fluid(tank.pop("fluid"), namespace, excluded, withheld)
            if replacement:
                tank["fluid"] = replacement
            else:
                for key in ("filter", "recipe", "timer"):
                    (tank if key == "filter" else result).pop(key, None)
                tank["capacity"] = Int(0)
        elif "FluidName" in tank:
            replacement = fluid(tank, namespace, excluded, withheld)
            result["tank"] = Compound({"Fluid": replacement}) if replacement else Compound()
        if "filter" in tank:
            tank["filter"] = renamed(tank["filter"], namespace)
    for key in ("drained", "render_fluid"):
        if key in result:
            result[key] = fluid(result[key], namespace, excluded, withheld)
    if "Items" in result:
        entries = (item(stack, namespace, excluded, withheld) for stack in result["Items"])
        result["Items"] = List[Compound](entry for entry in entries if entry is not None)
    inventory = result.get("inventory")
    if inventory and "items" in inventory:
        entries = (item(stack, namespace, excluded, withheld) for stack in inventory["items"])
        inventory["items"] = List[Compound](entry for entry in entries if entry is not None)
    return result


def smeltery_blocks(chunk, prefix=LEGACY):
    for section in chunk.get("sections", []):
        block_states = section.get("block_states", {})
        palette = block_states.get("palette", [])
        indices = {index for index, value in enumerate(palette) if value["Name"].startswith(prefix)}
        if not indices:
            continue
        bits = max(4, (len(palette) - 1).bit_length())
        per_long = 64 // bits
        mask = (1 << bits) - 1
        data = block_states.get("data", [])
        for index in range(4096):
            state = (int(data[index // per_long]) >> (index % per_long * bits)) & mask if len(data) else 0
            if state in indices:
                yield (
                    int(chunk["xPos"]) * 16 + index % 16,
                    int(section["Y"]) * 16 + index // 256,
                    int(chunk["zPos"]) * 16 + index // 16 % 16,
                ), palette[state]


def within(pos, minimum, maximum, margin):
    return all(lo - extra <= value <= hi + extra
               for value, lo, hi, extra in zip(pos, minimum, maximum, margin))


def bounds(controller):
    origin = position(controller)
    structure = controller["multiblock"]
    return [tuple(value + int(delta) for value, delta in zip(origin, offset(structure[key])))
            for key in ("min", "max")]


def save_template(output, states, entities, namespace, palette_ids, excluded):
    footprint = sorted(states)
    origin = tuple(min(pos[axis] for pos in footprint) for axis in range(3))
    size = [max(pos[axis] for pos in footprint) - origin[axis] + 1 for axis in range(3)]
    palette = []
    keys = {}
    records = []
    withheld = Counter()
    unresolved = []
    for pos in footprint:
        state = deepcopy(states[pos])
        state["Name"] = renamed(state["Name"], namespace)
        if state["Name"] not in palette_ids:
            raise ValueError(f"Target JAR has no block state resource for {state['Name']}")
        key = state.snbt()
        if key not in keys:
            keys[key] = len(palette)
            palette.append(state)
        record = Compound({
            "pos": List[Int](value - minimum for value, minimum in zip(pos, origin)),
            "state": Int(keys[key]),
        })
        if pos in entities:
            before = sum(withheld.values())
            record["nbt"] = convert(entities[pos], namespace, excluded, withheld)
            if sum(withheld.values()) != before:
                unresolved.append(entities[pos])
        records.append(record)
    File({
        "DataVersion": Int(3955), "size": List[Int](size),
        "entities": List[Compound](), "palette": List[Compound](palette), "blocks": List[Compound](records),
    }, gzipped=True).save(output)
    if unresolved:
        File({"block_entities": List[Compound](unresolved)}, gzipped=True).save(
            output.with_name(output.stem + "_unresolved.nbt"))
    return {
        "origin": origin, "size": size, "blocks": len(records),
        "block_entities": sum("nbt" in record for record in records),
        "withheld": [{"kind": kind, "id": resource, "amount": amount}
                     for (kind, resource), amount in sorted(withheld.items())],
    }


def export(regions, namespace, target_jar, output, excluded):
    prefix = f"assets/{namespace}/blockstates/"
    with ZipFile(target_jar) as jar:
        palette_ids = {f"{namespace}:{name[len(prefix):-5]}" for name in jar.namelist()
                       if name.startswith(prefix) and name.endswith(".json")}
    entities, states = {}, {}
    for path in regions:
        for chunk in chunks(path):
            entities.update((position(be), be) for be in chunk.get("block_entities", [])
                            if be["id"].startswith(LEGACY))
            states.update(smeltery_blocks(chunk))
    controllers = sorted(pos for pos, be in entities.items() if be["id"] == "tconstruct:smeltery")
    if not controllers:
        raise ValueError("No legacy smeltery controllers in the supplied regions")
    controller_indices = {pos: index for index, pos in enumerate(controllers)}
    boxes = [bounds(entities[pos]) for pos in controllers]
    selections = [{} for _ in controllers]
    for pos, state in states.items():
        nearby = [index for index, (lo, hi) in enumerate(boxes) if within(pos, lo, hi, (5, 3, 5))]
        if not nearby:
            continue
        entity = entities.get(pos, {})
        if "masterOffset" in entity:
            master = tuple(value + int(delta) for value, delta in zip(pos, offset(entity["masterOffset"])))
            owner = controller_indices.get(master)
            if owner in nearby:
                selections[owner][pos] = state
                continue

        def distance(index):
            lo, hi = boxes[index]
            return (sum(max(lower - value, value - upper, 0) for value, lower, upper in zip(pos, lo, hi)),
                    sum(abs(a - b) for a, b in zip(pos, controllers[index])))
        selections[min(nearby, key=distance)][pos] = state
    if output.exists():
        raise FileExistsError(output)
    with TemporaryDirectory(dir=output.parent) as temporary:
        payload = Path(temporary) / "export"
        payload.mkdir()
        report = []
        for index, (controller, selection) in enumerate(zip(controllers, selections), start=1):
            if controller not in selection:
                raise ValueError(f"Controller palette is missing at {controller}")
            row = save_template(payload / f"smeltery_{index}.nbt", selection, entities,
                                namespace, palette_ids, excluded)
            report.append({"controller": controller, **row})
        (payload / "transfer.json").write_text(json.dumps(report, indent=2) + "\n")
        payload.rename(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", choices=("tconstruct", "modernfoundry"), required=True)
    parser.add_argument("--target-jar", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--hold", action="append", default=[], help="Leave an absent item or fluid in the transfer report")
    parser.add_argument("regions", type=Path, nargs="+")
    args = parser.parse_args()
    export(args.regions, args.namespace, args.target_jar, args.output, set(args.hold))
