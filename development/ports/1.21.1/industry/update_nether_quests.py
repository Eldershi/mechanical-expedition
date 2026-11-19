#!/usr/bin/env python3
"""Set the Nether quest prerequisites without changing existing quest IDs."""

import argparse
from pathlib import Path
import re


NETHER_VISIT = "667B8EFCF3ACD51D"
FOUNDRY_MATERIALS = "470156018DA261F4"
BLAZE_BURNER = "04004B46385E2AF2"
FOUNDRY = "5095EB55709B5982"


def update_chapter(text, selected=(BLAZE_BURNER, FOUNDRY)):
    for quest, prerequisite in ((BLAZE_BURNER, NETHER_VISIT), (FOUNDRY, FOUNDRY_MATERIALS)):
        if quest not in selected:
            continue
        block_pattern = re.compile(
            rf'^\t\t\{{\n(?:(?!^\t\t\}})[\s\S])*?^\t{{3}}id: "{quest}"\n'
            r'(?:(?!^\t\t\})[\s\S])*?^\t\t\}',
            re.MULTILINE,
        )
        match = block_pattern.search(text)
        if match is None:
            raise ValueError(f"Cannot find quest {quest}")
        updated, count = re.subn(
            r'^\t{3}dependencies: \[[^\]]*\]',
            f'\t\t\tdependencies: ["{prerequisite}"]',
            match.group(),
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ValueError(f"Expected a single dependency list for quest {quest}")
        text = text[:match.start()] + updated + text[match.end():]
    return text


def update(quests):
    chapters = quests / "chapters"
    canonical = chapters / "steam_railway.snbt"
    updates = {}
    found = set()
    if not canonical.is_file():
        raise FileNotFoundError(canonical)
    for chapter in sorted(chapters.glob("steam_railway*.snbt")):
        original = chapter.read_text(encoding="utf-8")
        if chapter == canonical or re.search(r'^\tfilename: "steam_railway"$', original, re.MULTILINE):
            selected = {quest for quest in (BLAZE_BURNER, FOUNDRY) if f'\n\t\t\tid: "{quest}"\n' in original}
            updated = update_chapter(original, selected)
            found.update(selected)
            updates[chapter] = (original, updated)
    if missing := {BLAZE_BURNER, FOUNDRY} - found:
        raise ValueError(f"Missing Steam Railway quests: {', '.join(sorted(missing))}")
    for chapter, (original, updated) in updates.items():
        if updated != original:
            chapter.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quests", type=Path)
    update(parser.parse_args().quests)
