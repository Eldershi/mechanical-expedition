#!/usr/bin/env python3
"""Extract plain-text Create clipboard pages as guarded NeoForge commands."""

import argparse
import json
from pathlib import Path

import nbtlib
from measure_chunk_edges import read_chunk


COMPONENT = 'components."create:clipboard_content"'
CLIPBOARD_TYPES = ("empty", "written", "editing")


def recover(region, position):
    x, y, z = position
    chunk = read_chunk(region, x // 16, z // 16)
    if chunk is None:
        raise ValueError(f"Missing source chunk for {position}")
    clipboard, = (entry for entry in chunk.get("block_entities", ())
                  if entry["id"] == "create:clipboard" and tuple(int(entry[axis]) for axis in "xyz") == position)
    old = clipboard["Item"]["tag"]
    if set(old) - {"Type", "Pages", "PreviouslyOpenedPage", "Readonly"}:
        raise ValueError(f"Unrecognized clipboard metadata for {position}")
    pages = []
    for page in old["Pages"]:
        entries = []
        for line in page["Entries"]:
            text = json.loads(str(line["Text"]))
            if set(line) != {"Checked", "Text"} or not isinstance(text, dict) or set(text) != {"text"}:
                raise ValueError(f"Unsupported rich entry for {position}")
            entries.append(nbtlib.Compound({
                "checked": nbtlib.Byte(bool(line["Checked"])),
                "text": nbtlib.Compound({"text": nbtlib.String(text["text"])}),
                "icon": nbtlib.Compound(),
                "item_amount": nbtlib.Int(0),
            }))
        pages.append(nbtlib.List[nbtlib.Compound](entries))
    if not any(pages):
        raise ValueError(f"No pages to recover for {position}")
    return nbtlib.Compound({
        "type": nbtlib.String(CLIPBOARD_TYPES[int(old["Type"])]),
        "pages": nbtlib.List[nbtlib.List](pages),
        "previously_opened_page": nbtlib.Int(int(old.get("PreviouslyOpenedPage", 0))),
        "read_only": nbtlib.Byte(bool(old.get("Readonly", 0))),
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--position", action="append", nargs=3, type=int, required=True)
    args = parser.parse_args()
    commands = []
    for position in args.position:
        component = recover(args.source, tuple(position))
        location = " ".join(map(str, position))
        commands.append(
            f"execute in minecraft:overworld if block {location} create:clipboard "
            f"unless data block {location} {COMPONENT}.pages[][0] "
            f"run data modify block {location} {COMPONENT} set value {component.snbt(compact=True)}"
        )
    args.output.write_text("\n".join(commands) + "\n")


if __name__ == "__main__":
    main()
