#!/usr/bin/env python3
"""Install the current processing quests and remove unused Thermal assets."""

import argparse
import json
from pathlib import Path
import re

from update_graphite_quest import repair_locale_arrays

REMOVED_CHAPTER = "staged_technology_b_thermal_units"
CHAPTER_KEY = "484C7E988098F21B"
REMOVED_OIL_QUESTS = ("474F3BFA9CB14470", "611127197D19F6C0")
ICONS = {
    "thermal:bronze_ingot": "alltheores:bronze_ingot",
    "thermal:constantan_gear": "alltheores:constantan_gear",
    "thermal:raw_nickel": "alltheores:raw_nickel",
    "thermal:silver_gear": "alltheores:silver_gear",
    "thermal:silver_ingot": "alltheores:silver_ingot",
    "thermal:electrum_plate": "alltheores:electrum_plate",
    "thermal:nickel_ingot": "alltheores:nickel_ingot",
    "thermal:constantan_ingot": "alltheores:constantan_ingot",
    "thermal:quartz_dust": "mekanism:dust_quartz",
    "thermal:dynamo_stirling": "mekanismgenerators:heat_generator",
    "thermal_extra:polyolefin_bucket": "cmi:structural_plastic_bucket",
}
TITLES = {
    "12DB131FFA083A5E": "建造通用机械热蒸馏塔",
    "304F1C5501224675": "接入沉浸工程自动组装机",
    "4261BB2F0B43ACE2": "可选通用机械热能发电机",
    "497F194549E2E457": "用植物油和石脑油炼制润滑油",
    "594186D5FEE7CDF6": "柴油裂化制结构塑料",
}
PROCESSES = {
    "12DB131FFA083A5E": (
        "制作通用机械蒸馏控制器，与蒸馏方块和阀门组成热蒸馏塔。",
        "用阀门输入水并输出盐水。需要提炼锂时，再用独立蒸馏塔处理盐水。",
    ),
    "304F1C5501224675": (
        "在工程师工作台准备工程零件，建造沉浸工程自动组装机并接入 FE。",
        "在自动组装机界面设定工作台合成图样，分别供应各槽材料。",
    ),
    "594186D5FEE7CDF6": (
        "柴油和蒸汽裂化后，用馏分塔分出轻醛和乙炔。",
        "用乙炔加工出聚乙烯醇，再和轻醛一起送入沉浸工程精炼厂，制成结构塑料。",
    ),
    "497F194549E2E457": (
        "在沉浸工程精炼厂用铜板作催化片，配植物油 100 mB 和石脑油 100 mB，制润滑油 200 mB。",
    ),
    "4261BB2F0B43ACE2": (
        "制作通用机械热能发电机，接真实负载查看输出。可用燃料，也可利用附近热源。",
    ),
    "7629E771DA8DD67D": (
        "粗钋的结晶工序待接入机巧新生气密反应釜。",
    ),
    "5803FBD4426BF611": (
        "钚电离结晶的结晶工序待接入机巧新生气密反应釜。",
    ),
}
LINES = {
    "可选自动普通合成支路。不以它替代热力组件装配机。": "可用沉浸工程自动组装机批量完成工作台配方。",
    "压板制热力单元，或用于不锈钢添加剂。": "按对应配方制金属板或用作不锈钢添加剂。",
    "木屑可用焦炉配方。热力锯木机为另一条并行路线。": "木屑可用沉浸工程焦炉加工。",
    "配方查询同时保留基片加液态乙烯加氧的PRC配方，以及HDPE流体热力吸热冷凝路线。两种配方为任选一种，本图选PRC工艺示例，不能要求两条都建。": "HDPE 使用通用机械加压反应室，投入基片、液态乙烯和氧气。",
    "按需求并联更多供能或换柴油/热力。": "按需求并联更多供能或换柴油发电。",
    "统一配方使用硫粉与2糖。不是要求先建热力机器。": "统一配方使用硫粉和 2 份糖。",
    "选择热力灌装结构玻璃配方，供料供液，收结构玻璃。": "沉浸工程灌装机用 200 mB 结构塑料灌装石英玻璃，得到结构玻璃。",
    "如果您碰到由热力系列(指名道姓&c狂风人&r和&c岩石人&r)添加的拥有远程攻击能力的怪物, 就用它进行反击吧. ": "遇到会远程攻击的怪物，例如骷髅，可用盾牌格挡。",
    "输入对应真实燃料，核能量输出面并接有需求负载。热力熔岩燃料已由数据覆写。": "投入当前发电机支持的燃料，把能量输出面接到真实负载。",
    "给热力或沉浸机器供FE。": "给沉浸工程机器或其他用电设备供 FE。",
    "CMI 路线需要安山漏斗、安山构件与黄铜板；当前另有原生并行配方。两条配方只影响制作成本，过滤和红石行为相同。": "使用机械动力的黄铜漏斗配方。过滤和红石控制按同一套操作。",
    "本包动力臂仍走黄铜板、小型青铜弹簧、安山构件、精密构件与黄铜机壳的魔改配方。": "使用机械动力原生配方制作动力臂，再配置输入和输出位置。",
    "CMI 路线需要安山构件、工业铁板等，已有原生并行配方。一个订单中的原料比例必须按当前魔改配方填写，机器不会自动识别你希望制作的构件。": "按当前 JEI 配方填写订单原料比例，机器按订单拆包和配料。",
    "CMI 路线需要安山构件、弹簧等材料，当前也有原生并行配方。蛙港负责包裹运输，不会自动替工厂计算魔改配方的需求数量。": "按 JEI 配方制作蛙港。蛙港负责包裹运输，订单负责指定配料数量。",
    "本包的置物台加安山构件配方与原生并行配方都可制作。用批量弹射给构件线供料前，先核对当前配方每循环的真实消耗。": "使用机械动力的置物台和弹射工位，按配方用量批量供料。",
    "CMI 配方需要安山构件、工业铁板、纸板块等；当前原生配方并行。魔改生产线要按实际配方配好一包的原料，再交给拆包工位。": "按当前 JEI 配方配好一包的原料，再交给拆包工位。",
    "CMI 配方需要安山构件、金板、发信器与机壳，当前也有原生配方。魔改装配的订货数量应按每轮消耗计算，缺一项会使后续工位等待。": "按当前 JEI 配方计算每轮原料用量，缺料会使后续工位等待。",
    "本包保留安山隧道加安山构件、黄铜板的升级配方，也有原生并行配方。先为各工序设成品过滤，再决定是否需要严格等比例供料。": "使用机械动力的黄铜隧道配方，并为各工序设置成品过滤。",
    "本包保留溜槽加安山构件、黄铜板的 CMI 升级配方，同时补回原生配方。数量限制用于分批投料，实际配方所需数量仍须查当前 JEI。": "使用机械动力的智能溜槽配方。设置数量限制可分批投料。",
}


def quote(line):
    return json.dumps(line, ensure_ascii=False)


def description(lines, indent):
    return "[\n" + "".join(indent + "\t" + quote(line) + "\n" for line in lines) + indent + "]"


def remove_oil_nodes(text):
    for quest in REMOVED_OIL_QUESTS:
        top_level_node = r'(?ms)^\t\t\{\n(?:(?!^\t\t\}).)*^\t\t\}\n'
        text = re.sub(
            top_level_node,
            lambda m: "" if (
                f'id: "{quest}"' in m[0] or f'"q:{quest.lower()}"' in m[0]
            ) else m[0],
            text,
        )
    return text


def update_chapter(text):
    def update_node(match):
        block = match[0]
        id_match = re.search(r'(?m)^\t\t\tid: "([0-9A-F]{16})"', block)
        if not id_match:
            return block
        quest = id_match[1]
        if quest == "304F1C5501224675":
            block = block.replace('icon: "create:mechanical_crafter"', 'icon: "immersiveengineering:assembler"')
        if quest in TITLES:
            block = re.sub(r'(?m)^(\t\t\ttitle: )"[^"\n]*"', lambda m: m[1]+quote(TITLES[quest]), block)
        if quest in PROCESSES:
            block = re.sub(r'(?ms)^(\t\t\tdescription: )\[\n.*?^\t\t\t\]',
                           lambda m: m[1]+description(PROCESSES[quest], "\t\t\t"), block)
        return block

    text = remove_oil_nodes(text)
    for old, new in ICONS.items():
        text = text.replace(quote(old), quote(new))
    for old, new in LINES.items():
        text = text.replace(quote(old), quote(new))
    return re.sub(r'(?ms)^\t\t\{\n.*?^\t\t\}\n', update_node, text)


def update_locale(text):
    prop = re.compile(
        r'(?ms)^\t(quest|chapter)\.([0-9A-F]{16})\.([a-z_.]+): '
        r'(\[\n.*?^\t\]|[^\n]*)\n'
    )
    def update(match):
        kind, quest, key, value = match.groups()
        if quest == CHAPTER_KEY or quest in REMOVED_OIL_QUESTS:
            return ""
        if kind == "quest" and key == "title" and quest in TITLES:
            value = quote(TITLES[quest])
        elif kind == "quest" and key == "quest_desc" and quest in PROCESSES:
            value = description(PROCESSES[quest], "\t")
        else:
            for old, new in LINES.items():
                value = value.replace(quote(old), quote(new))
        return f"\t{kind}.{quest}.{key}: {value}\n"
    return repair_locale_arrays(prop.sub(update, text))


def install(instance):
    quests = instance / "config/ftbquests/quests"
    chapters = quests / "chapters"
    if not chapters.is_dir():
        raise ValueError("FTB Quests chapters directory is required")
    (chapters / (REMOVED_CHAPTER+".snbt")).unlink(missing_ok=True)
    for file in chapters.glob("*.snbt"):
        text = file.read_text()
        updated = update_chapter(text)
        if file.stem == "research_technology_b_thermal":
            destination = file.with_name("research_technology_b_processing.snbt")
            if destination.exists():
                raise ValueError(f"Processing chapter already exists: {destination}")
            destination.write_text(updated.replace(file.stem, destination.stem))
            file.unlink()
        elif updated != text:
            file.write_text(updated)
    for file in (quests / "lang").glob("*.snbt"):
        text = file.read_text()
        updated = update_locale(text)
        if updated != text:
            file.write_text(updated)
    assets = instance / "kubejs/assets/cmi"
    for pattern in (
        "textures/item/material/mold/clay/*.png",
        "textures/item/material/unit/*.png",
        "textures/item/component/*cell.png",
        "textures/item/mechanism/*/thermal.png",
        "textures/item/material/incomplete/thermal_mechanism_augment.png",
        "textures/item/mechanism/*/andesite.png",
        "textures/painting/driver_thermal.png",
        "textures/block/machine/ue/thermal_machine.png",
        "models/block/machine_block/thermal.json",
        "ponder/thermal/*.nbt",
        "ponder/dev_ftb/ftb_thermal.nbt",
        "textures/block/io_debug/ponder_thermal_*.png",
    ):
        for file in assets.glob(pattern):
            if pattern.endswith("unit/*.png") and file.stem not in {"thermal", "blaze", "basalz", "blizz", "blitz"}:
                continue
            if pattern.endswith("/*cell.png") and file.stem not in {"basalz_cell", "blizz_cell", "blitz_cell"}:
                continue
            if "mechanism/*/andesite.png" in pattern and file.parent.name not in {"complete", "incomplete"}:
                continue
            file.unlink()
            if file.suffix == ".png":
                file.with_suffix(".png.mcmeta").unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instance", type=Path)
    install(parser.parse_args().instance)
