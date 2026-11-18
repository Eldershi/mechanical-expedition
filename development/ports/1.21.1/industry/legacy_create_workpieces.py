"""Translate verified Create item state from 1.20.1 to 1.21.1 components."""

from math import isclose

from nbtlib import Byte, Compound, Float, Int, IntArray, String


ASSEMBLY_STATES = {
    "cmi:incomplete_copper_mechanism": (
        "create:kjs/elmz0havrfy39lpkztirwnlib_449", "expedition:industry/copper_mechanism", 1, 5,
    ),
    "create:incomplete_precision_mechanism": (
        "create:sequenced_assembly/precision_mechanism", "expedition:factory/electrical/precision_mechanism", 2, 5,
    ),
    "cmi:incomplete_light_engineering_mechanism": (
        "create:kjs/elmz0havrfy39lpkztirwnlib_557", "expedition:factory/mechanisms/light_engineering", 1, 6,
    ),
    "cmi:incomplete_motor_rotor": (
        "create:kjs/elmz0havrfy39lpkztirwnlib_101", "expedition:factory/electrical/motor_rotor", 1, 3,
    ),
}
UNUSED_TOOLS = {"create:sand_paper", "create:super_glue"}
BELT_CONNECTOR = "create:belt_connector"
WORKPIECES = UNUSED_TOOLS | ASSEMBLY_STATES.keys() | {BELT_CONNECTOR}


def convert_assembly(item, payload):
    old_recipe, new_recipe, expected_step, total_steps = ASSEMBLY_STATES[item]
    assembly = payload.get("SequencedAssembly")
    if (set(payload) != {"SequencedAssembly"} or not isinstance(assembly, Compound)
            or set(assembly) != {"id", "Step", "Progress"} or assembly["id"] != old_recipe
            or not isinstance(assembly["Step"], Int) or assembly["Step"] != expected_step
            or not isinstance(assembly["Progress"], Float)
            or not isclose(assembly["Progress"], expected_step / total_steps, abs_tol=1e-7)):
        raise ValueError("Unverified legacy Create recipe or stage")
    return Compound({"create:sequenced_assembly": Compound({
        "id": String(new_recipe), "step": Int(expected_step), "progress": assembly["Progress"],
    })})


def convert_create_workpiece(original):
    item = str(original.get("id", ""))
    payload = original.get("tag")
    if (item not in WORKPIECES or set(original) != {"id", "Count", "Slot", "tag"}
            or not isinstance(payload, Compound) or not isinstance(original["Count"], Byte)):
        raise ValueError("Unverified Create item fields")
    count = int(original["Count"])
    if not 1 <= count <= (64 if item == BELT_CONNECTOR else 1):
        raise ValueError("Invalid Create item quantity")

    stack = Compound({"id": String(item), "count": Int(count)})
    if item in ASSEMBLY_STATES:
        stack["components"] = convert_assembly(item, payload)
    elif item == BELT_CONNECTOR:
        pulley = payload.get("FirstPulley")
        if (set(payload) != {"FirstPulley"} or not isinstance(pulley, Compound)
                or set(pulley) != {"X", "Y", "Z"} or not all(isinstance(pulley[axis], Int) for axis in "XYZ")):
            raise ValueError("Unverified Create belt shaft selection")
        stack["components"] = Compound({"create:belt_first_shaft": IntArray([pulley[axis] for axis in "XYZ"])})
    elif set(payload) != {"Damage"} or not isinstance(payload["Damage"], Int) or payload["Damage"] != 0:
        raise ValueError("Only unworn Create tools are covered by this mapping")
    return stack
