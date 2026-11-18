"""Convert supported Iron's Spells 'n Spellbooks NBT into 1.21.1 components."""

from copy import deepcopy
import re

from nbtlib import Compound, Int, String


SPELL_CONTAINER = "irons_spellbooks:spell_container"
AFFINITY_DATA = "irons_spellbooks:affinity_data"
SPELL_DATA = {SPELL_CONTAINER, AFFINITY_DATA}
ID = re.compile(r"[a-z0-9_.-]+:[a-z0-9_/.-]+")


def _valid_spell_slots(container):
    capacity = container.get("maxSpells")
    if not isinstance(capacity, int) or capacity < 0:
        return False
    if not all(container.get(key) in (0, 1) for key in ("spellWheel", "mustEquip")):
        return False
    if not isinstance(container.get("data"), list):
        return False

    indices = set()
    for slot in container["data"]:
        if not isinstance(slot, Compound):
            return False
        index = slot.get("index")
        level = slot.get("level")
        if (not isinstance(index, int) or not 0 <= index < capacity or index in indices
                or not isinstance(level, int) or level <= 0 or not ID.fullmatch(str(slot.get("id", "")))):
            return False
        indices.add(index)
    return True


def spell_components(legacy_tag):
    """Copy the original spell and affinity components in the current codec shape."""
    components = Compound()
    for key in SPELL_DATA & legacy_tag.keys():
        value = legacy_tag[key]
        if not isinstance(value, Compound):
            raise ValueError(f"Unsupported {key} payload")
        if key == SPELL_CONTAINER and not _valid_spell_slots(value):
            raise ValueError("Unsupported spell container slots")
        if key == AFFINITY_DATA:
            bonuses = value.get("bonuses")
            if not isinstance(bonuses, Compound) or not all(
                    ID.fullmatch(spell) and isinstance(level, int) for spell, level in bonuses.items()):
                raise ValueError("Unsupported spell affinity bonuses")
        components[key] = deepcopy(value)
    return components


def convert_scroll(source):
    """Convert a scroll whose only legacy metadata is its native spell container."""
    if source.get("id") != "irons_spellbooks:scroll" or not source.keys() <= {"id", "Count", "Slot", "tag"}:
        raise ValueError("Expected an unmodified legacy Iron's Spells scroll")
    tag = source.get("tag", {})
    count = source.get("Count", 0)
    if tag.keys() != {SPELL_CONTAINER} or not isinstance(count, int) or not 1 <= count <= 64:
        raise ValueError("Unsupported scroll count or metadata")
    stack = Compound({"id": String(source["id"]), "count": Int(count), "components": spell_components(tag)})
    if "Slot" in source:
        stack["Slot"] = Int(source["Slot"])
    return stack
