#!/usr/bin/env python3
"""Build Expedition's native Create 1.21.1 construction schematics from installed mods."""
import argparse
from collections import Counter
from gzip import compress, decompress
from io import BytesIO
from itertools import product
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from nbtlib import Compound, File, Int, List, String, parse_nbt

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "world-server/brass-industry"))
from hydropress.model import construction as press_construction
from worksites.models import SITES

DATA_VERSION = 3955
AIR = {"minecraft:air", "minecraft:cave_air", "minecraft:void_air", "minecraft:structure_void"}
MEKANISM = {
    "boiler": "热力锅炉",
    "evaporation_tower": "热力蒸馏塔",
    "fission_reactor": "裂变反应堆",
    "fusion_reactor": "聚变反应堆",
    "sps": "超临界移相器",
    "turbine": "工业涡轮",
}
IE = {
    "alloy_smelter": "合金窑",
    "arcfurnace": "电弧炉",
    "assembler": "装配机",
    "auto_workbench": "自动化工程师装配台",
    "blast_furnace": "高炉",
    "bottling_machine": "灌装机",
    "bucket_wheel": "斗轮",
    "chunk_loader": "区块加载器",
    "coke_oven": "焦炉",
    "crusher": "粉碎机",
    "diesel_generator": "柴油发电机",
    "excavator": "挖掘机主体",
    "excavator_full": "斗轮式挖掘机（完整）",
    "fermenter": "工业发酵机",
    "improved_blast_furnace": "强化高炉",
    "lightning_rod": "避雷针基座",
    "metal_press": "金属冲压机",
    "mixer": "搅拌机",
    "radio_tower": "无线电塔",
    "refinery": "炼油厂",
    "sawmill": "锯木机",
    "sheetmetal_tank": "流体储罐",
    "shelf": "板条货架",
    "silo": "储物筒仓",
    "squeezer": "工业挤压机",
}


def jar(mods, filename):
    path = mods / filename
    if not path.is_file():
        raise FileNotFoundError(f"Expected mod: {filename}")
    return ZipFile(path)


def read_structure(archive, name):
    blob = archive.read(name)
    if blob.startswith(b"\x1f\x8b"):
        blob = decompress(blob)
    return File.parse(BytesIO(blob))


def palette_entry(name, properties=None):
    result = Compound({"Name": String(name)})
    if properties:
        result["Properties"] = Compound({k: String(v) for k, v in properties.items()})
    return result


def unformed(state):
    # Retain facings, port modes and other placement states. Recalculate operation states in-world.
    state = Compound(state)
    props = Compound(state.get("Properties", {}))
    for key in ("active", "formed", "multiblocked", "powered", "powered_on", "in_structure", "slave"):
        if props.get(key) == "true":
            # SPS port active is a flow mode, set manually after construction.
            props[key] = String("false")
    if props:
        state["Properties"] = props
    return state


def vanilla_blocks(template):
    for block in template["blocks"]:
        yield tuple(map(int, block["pos"])), unformed(template["palette"][int(block["state"])])


def guide_blocks(template, excluded=()):
    for block in template["data"]:
        name, brace, properties = str(block["state"]).partition("{")
        if name in excluded:
            continue
        states = {}
        if brace:
            for pair in properties.removesuffix("}").split(","):
                key, value = pair.split(":", 1)
                states[key] = value.strip('"')
        yield tuple(map(int, block["pos"])), unformed(palette_entry(name, states))


def solid_structure(dimensions, entries):
    palette, states, blocks = [], {}, []
    for position, state in sorted(entries, key=lambda entry: (entry[0][1], entry[0][0], entry[0][2])):
        if str(state["Name"]) in AIR:
            continue
        if not all(0 <= coord < size for coord, size in zip(position, dimensions, strict=True)):
            raise ValueError(f"Block outside structure: {position} in {dimensions}")
        signature = (str(state["Name"]), tuple(sorted(state.get("Properties", {}).items())))
        index = states.setdefault(signature, len(palette))
        if index == len(palette):
            palette.append(state)
        blocks.append(Compound({"pos": List[Int](position), "state": Int(index)}))
    positions = {tuple(block["pos"]) for block in blocks}
    if not positions or len(positions) != len(blocks):
        raise ValueError("Empty structure or repeated block position")
    return File({
        "DataVersion": Int(DATA_VERSION), "size": List[Int](dimensions),
        "palette": List[Compound](palette), "blocks": List[Compound](blocks),
        "entities": List[Compound](),
    })


def casing_cube(size, casing, special, fill=None):
    for pos in product(range(size), repeat=3):
        default = casing if any(n in (0, size - 1) for n in pos) else fill
        name = special.get(pos, default)
        if name is not None:
            yield pos, palette_entry(name)


def radar_blocks():
    fixture = ROOT.parent / "radar-mbd2/tests/assembly.tsv"
    for row in fixture.read_text(encoding="utf-8").splitlines():
        x, y, z, name = row.split("\t")
        properties = {"facing": "east"} if name == "cmi:radar_antenna" else {}
        yield (int(x), int(y), int(z)), palette_entry(name, properties)


def get_catalog(mods):
    catalog = {}

    def add(group, name, label, dimensions, blocks, note=""):
        filename = f"Expedition_{group}_{name}.nbt"
        if filename in catalog:
            raise ValueError(f"Duplicate template: {filename}")
        catalog[filename] = (label, solid_structure(dimensions, blocks), note)

    with jar(mods, "ImmersiveEngineering-1.21.1-12.4.2-194.jar") as source:
        for name, label in IE.items():
            template = read_structure(source, f"data/immersiveengineering/structure/multiblocks/{name}.nbt")
            note = "按工程师手册提示，用工程师锤右击成型点。"
            if name == "bucket_wheel":
                note = "用于搭建挖掘机的斗轮；整机施工可选完整挖掘机蓝图。"
            add("IE", name, label, template["size"], vanilla_blocks(template), note)

    with jar(mods, "MultiBuilderTool-1.21.1-1.1.31.jar") as source:
        for name, label in MEKANISM.items():
            template = read_structure(source, f"data/mbtool/mbtool_structures/mekanism_{name}.nbt")
            note = "结构由通用机械识别。成型后检查接口和供给。"
            if name == "turbine":
                rotors = sum(1 for _, state in vanilla_blocks(template) if state["Name"] == "mekanismgenerators:turbine_rotor")
                note = f"施工后装 {rotors * 2} 片涡轮叶片，每根转子 2 片，再接入蒸汽。"
            if name == "sps":
                note = "施工后使用配置器设置输入和输出端口，再按设备说明接线。"
            add("Mekanism", name, label, template["size"], vanilla_blocks(template), note)

    for size in (3, 5):
        mid = size // 2
        add("Mekanism", f"dynamic_tank_{size}x{size}x{size}", "动态储罐", (size,) * 3,
            casing_cube(size, "mekanism:dynamic_tank", {(0, mid, mid): "mekanism:dynamic_valve"}),
            "结构由通用机械识别。阀门用于输入或输出流体和化学品。")
    add("Mekanism", "induction_matrix_3x3x4", "感应矩阵（含供应器）", (3, 3, 4),
        ((pos, palette_entry(
            {(1, 1, 1): "mekanism:basic_induction_cell", (1, 1, 2): "mekanism:basic_induction_provider",
             (0, 1, 1): "mekanism:induction_port", (2, 1, 1): "mekanism:induction_port"}
            .get(pos, "mekanism:induction_casing")))
         for pos in product(range(3), range(3), range(4))),
        "建成后用配置器将一侧端口切换为输出，另一侧接入电源。")

    with jar(mods, "TinkersConstruct-Unofficial-Port-1.21.1-1.6.1-NeoForge.jar") as source:
        for name, label in {"smeltery": "冶炼炉", "foundry": "熔铸炉"}.items():
            template = read_structure(source, f"assets/modernfoundry/book/structures/{name}.nbt")
            blocks = ((pos, Compound(state, Name=String(str(state["Name"]).replace("tconstruct:", "modernfoundry:"))))
                      for pos, state in vanilla_blocks(template))
            add("Foundry", name, label, template["size"], blocks, "控制器会检测结构。成型后向储罐加入燃料。")

    guide_sources = [
        ("AdvancedAE-1.6.12-1.21.1.jar", "assets/advanced_ae/ae2guide/structure/quantum_computer_multiblock.snbt",
         "quantum_computer", "量子计算机", "保持唯一量子核心，施工后接入 ME 网络。", ()),
        ("ExtendedAE-1.21-2.2.43-neoforge.jar", "assets/extendedae/ae2guide/structure/assembler_matrix.snbt",
         "assembler_matrix", "装配矩阵", "施工后接入 ME 网络。", ()),
        ("extendedae_plus-1.6.4.2.jar", "assets/extendedae_plus/ae2guide/structure/super_assembler_matrix.snbt",
         "super_assembler_matrix", "超级装配矩阵", "施工后接入 ME 网络。", ()),
        ("appliedenergistics2-19.2.20.jar", "assets/ae2/ae2guide/assets/assemblies/better_spatial_storage_3x3x3.snbt",
         "spatial_storage_3x3x3", "空间存储（3×3×3 收纳区）", "参照 AE2 空间存储指南补上 ME 线缆，连接全部塔柱。", ("ae2:cable_bus",)),
    ]
    for filename, resource, name, label, note, excluded in guide_sources:
        with jar(mods, filename) as source:
            guide = parse_nbt(source.read(resource).decode("utf-8"))
        add("AE", name, label, guide["size"], guide_blocks(guide, excluded), note)
    add("AE", "quantum_network_bridge", "量子网络桥（单端）", (3, 3, 1),
        ((pos, palette_entry("ae2:quantum_link" if pos == (1, 1, 0) else "ae2:quantum_ring"))
         for pos in product(range(3), range(3), range(1))),
        "每端各搭一套，接入 ME 网络并放入配对的量子纠缠奇点。")
    add("AE", "me_controller_ring", "ME 控制器（平面环）", (3, 3, 1),
        ((pos, palette_entry("ae2:controller")) for pos in product(range(3), range(3), range(1)) if pos != (1, 1, 0)),
        "将同一套控制器接入 ME 网络并供电。")
    add("AE", "crafting_cpu", "合成 CPU", (2, 1, 1),
        [((0, 0, 0), palette_entry("ae2:1k_crafting_storage")), ((1, 0, 0), palette_entry("ae2:crafting_accelerator"))],
        "施工后接入 ME 网络。")

    add("CMI", "radar_antenna", "雷达天线", (4, 6, 3), radar_blocks(),
        "控制器朝向由蓝图保存。结构成型后为雷达充能，再放入对应任务的输入。")
    layout = json.loads((ROOT.parent / "world-server/brass-industry/alloy-furnace/layout.json").read_text())
    for family, label in (("andesite", "安山"), ("brass", "黄铜")):
        entries = (
            (tuple(cell["pos"]), palette_entry(
                f"create:{family}_funnel" if cell["block"] == "create:andesite_funnel" else cell["block"],
                cell.get("state")))
            for cell in layout["cells"]
        )
        add("CMI", f"alloy_furnace_{family}", f"合金炉（{label}漏斗）", layout["size"], entries,
            "放齐后由控制器识别。控制面相对蓝图朝西，烟道朝南，接线端为大型连接器。")
    press = press_construction()
    add("CMI", "hydropress", "液压机", press["size"],
        ((tuple(cell["pos"]), palette_entry(cell["block"], cell.get("state"))) for cell in press["cells"]),
        "北面操作，西面漏斗进料，东面槽口出料，南面接进液管，东后侧接大型连接器。")
    notes = {
        "shaft_furnace": "装入两座有烈焰人的液体燃烧室，按格对齐氧气、熔铁和出钢管。",
        "electrolytic_cell": "南面进液，分别为西、东侧产物管设置流体过滤。",
        "trading_station": "西侧收货蜂港保持红石供电，东侧发货蜂港保持无红石信号。给两港配置独立地址。",
    }
    for name, site in SITES.items():
        layout = site.construction()
        add("CMI", name, site.label, layout["size"],
            ((tuple(cell["pos"]), palette_entry(cell["block"],cell["state"])) for cell in layout["cells"]),
            notes[name])
    return catalog


def encode(template):
    raw = BytesIO()
    template.write(raw)
    return compress(raw.getvalue(), mtime=0)


def index(catalog):
    lines = ["# 远征多方块蓝图", "", "在机械动力蓝图桌选择以 Expedition_ 开头的文件。"
             "写入空白蓝图后，到施工点定位并开启预览。蓝图炮可以按材料清单施工。", "",
             "在空地定位蓝图，为设备内部留下空腔。对照每项的说明完成成型、接线及启动。", "",
             "戴森球的射线接收站和电磁轨道弹射器需要手持控制器对空地放置。"
             "控制器放置时会由戴森球模组创建设备主体。", "",
             "| 蓝图文件 | 结构 | 外尺寸（长×高×宽） | 施工后 |",
             "|---|---|---|---|"]
    for name, (label, template, note) in sorted(catalog.items()):
        size = "×".join(str(int(dim)) for dim in template["size"])
        lines.append(f"| `{name}` | {label} | {size} | {note} |")
    return "\n".join(lines) + "\n"


def install(files, destination):
    folder = destination / "schematics"
    folder.mkdir(parents=True, exist_ok=True)
    conflicts = [name for name, data in files.items()
                 if (folder / name).exists() and (folder / name).read_bytes() != data]
    if conflicts:
        raise FileExistsError("Back up the conflicting blueprints before installing: " + ", ".join(conflicts))
    for name, data in files.items():
        with NamedTemporaryFile(dir=folder, delete=False) as output:
            output.write(data)
        Path(output.name).replace(folder / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mods", type=Path, required=True, help="Expedition NeoForge mods directory")
    parser.add_argument("--output", type=Path, required=True, help="Output blueprint ZIP")
    parser.add_argument("--install", type=Path, help="Optional NeoForge client game folder")
    args = parser.parse_args()

    catalog = get_catalog(args.mods)
    files = {name: encode(template) for name, (_, template, _) in sorted(catalog.items())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(args.output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr(ZipInfo("蓝图目录.md"), index(catalog).encode("utf-8"), compress_type=ZIP_DEFLATED)
        for name, data in files.items():
            archive.writestr(ZipInfo(f"schematics/{name}"), data)
    if args.install:
        install(files, args.install)
    for name, (label, template, _) in sorted(catalog.items()):
        counts = Counter(str(template["palette"][int(block["state"])]["Name"]) for block in template["blocks"])
        print(f"{name}: {label} | {sum(counts.values())} blocks, {len(counts)} material types")
    print(f"Generated {len(files)} native Create schematics")


if __name__ == "__main__":
    main()
