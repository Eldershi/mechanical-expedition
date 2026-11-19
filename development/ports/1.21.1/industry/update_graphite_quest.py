#!/usr/bin/env python3
"""Update the HOP graphite instruction in the imported FTB quest data."""

import argparse
from pathlib import Path
import re


QUEST = "079E063C2BE0D4B6"
TITLE = "加热冲压 HOP 石墨锭"
DESCRIPTION = (
    "{image:expedition_research:textures/quests/7214de61317d12ce89e50113.png width:32 height:32 align:center}",
    "在工作盆上方装动力冲压机，下方放烈焰人燃烧室，用普通燃料加热。",
    "投入 8 份焦炭粉可压成 1 份 HOP 石墨粉，也可用沉浸工程挤压机供粉。",
    "投入 1 份 HOP 石墨粉，压成 1 枚 HOP 石墨锭并完成任务。",
    "石墨粉或石墨锭均可用机械动力注液器加入 100 mB 红石酸，制成活化石墨碎块。",
)


def replace_description(text, pattern):
    def replace(match):
        head, indent = match.groups()
        lines = "\n".join(f'{indent}\t"{line}"' for line in DESCRIPTION)
        return f"{head}\n{lines}\n{indent}]"

    result, count = re.subn(pattern, replace, text, count=1, flags=re.M | re.S)
    if count != 1:
        raise ValueError(f"Cannot find HOP graphite quest description: {QUEST}")
    return result


def repair_locale_arrays(text):
    # The imported locale uses one-tab keys and a one-tab closing bracket for arrays.
    lines = []
    in_array = False
    for line in text.splitlines(keepends=True):
        if re.fullmatch(r'\t[^\s:]+: \[\n?', line):
            in_array = True
        elif line.rstrip("\n") == "\t]":
            if not in_array:
                continue
            in_array = False
        lines.append(line)
    return "".join(lines)


def update(quests):
    chapter = quests / "chapters/research_technology_b_start.snbt"
    text = chapter.read_text()
    if re.search(rf'id: "{QUEST}"\s*\n\s+title:', text):
        title_pattern = rf'(id: "{QUEST}"\s*\n\s+title: )"[^"]*"'
        updated = re.sub(title_pattern, rf'\g<1>"{TITLE}"', text, count=1)
        description_pattern = rf'(id: "{QUEST}"(?:(?!\n\t\t\}}).)*?\n(\t{{3}})description: \[).*?\n\t{{3}}\]'
        chapter.write_text(replace_description(updated, description_pattern))

    for locale in (quests / "lang/en_us.snbt", quests / "lang/zh_cn.snbt"):
        if not locale.is_file():
            continue
        text = locale.read_text()
        quest = rf"quest\.{QUEST}"
        title_pattern = rf'({quest}\.title: )"[^"]*"'
        updated, count = re.subn(title_pattern, rf'\g<1>"{TITLE}"', text, count=1)
        if count:
            description_pattern = rf'^((\t){quest}\.quest_desc: \[).*?\n\t\]'
            updated = replace_description(updated, description_pattern)
            locale.write_text(repair_locale_arrays(updated))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("quests", type=Path)
    update(parser.parse_args().quests)
