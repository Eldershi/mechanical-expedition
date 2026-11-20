#!/usr/bin/env python3
"""Install the CMI registrations supported by the NeoForge KubeJS build."""

import argparse
from pathlib import Path
import re
import shutil
from zipfile import ZipFile


HERE = Path(__file__).resolve().parent
MATERIALS = ("Dusts", "Gears", "Gems", "Ingots", "Plates", "RawOres", "Rods", "Wafer", "Wires")
ITEMS = ("Basic", "Cells", "Incompletes", "Molds")
MECHANISMS = ("Augment", "Basement", "Flashdrive", "Parts")
SOURCE_FILES = (
    *(f"material/{name}.js" for name in MATERIALS),
    *(f"item/{name}.js" for name in ITEMS),
    *(f"item/mechanism/{name}.js" for name in MECHANISMS),
    "other/Cast.js",
)
MODEL_CALL = re.compile(r"\.modelJson\((\{.*?\}|[\w.]+\([^()]*\))\)", re.S)
OLD_TAG = re.compile(r"""(\.tag\(["'`])forge:""")
THERMAL_TAG = re.compile(r"""(?m)^[ \t]*\.tag\(["'`]thermal:[^\n]*\n""")
GRASS_STRING = re.compile(
    r'(?m)^\t// 草绳\n\taddMaterial\("grass_string"\)\n(?:\t\t\.tag\([^\n]+\n)*\n'
)
PEAT_ITEM = re.compile(
    r'(?m)^\t// 泥炭\n\taddItem\("peat"\)\n'
    r'\t\t\.texture\([^\n]+\n\t\t\.burnTime\(800\)\n\n'
)
OBSIDIAN_CELL = re.compile(
    r'(?m)^\t// 黑曜石元件\n\tadd(?:Item|Material)\("obsidian_cell"\)\n'
    r'(?:\t\t\.texture\([^\n]+\n)?\n'
)
ENRICHED_SILICON = re.compile(r'(?m)^\t// 富集硅\n\taddNonGemItem\("enriched_silicon"\)\n')
RETIRED_COLLECTIBLES = re.compile(
    r'(?m)^(?:\t// (?:寒霜蛋糕胚|羊皮纸)\n)?'
    r'\tadd(?:Item|Material)\("(?:frost_cake_base|parchment|torn_parchment_[ab])"\)\n(?:\t\t\.[^\n]+\n)*'
)


def remove_retired_items(source):
    updated = OBSIDIAN_CELL.sub("", PEAT_ITEM.sub("", GRASS_STRING.sub("", source)))
    updated = RETIRED_COLLECTIBLES.sub("", updated)
    if re.search(r'add(?:Item|Material)\("(?:grass_string|peat|obsidian_cell|frost_cake_base|parchment|torn_parchment_[ab])"\)', updated):
        raise ValueError("Unexpected retired item registration")
    return updated


def retire_items(instance):
    basic = instance / "kubejs/startup_scripts/cmi/item/Basic.js"
    original = basic.read_text(encoding="utf-8")
    updated = remove_retired_items(original)
    if updated != original:
        basic.write_text(updated, encoding="utf-8")
    gems = basic.parents[1] / "material/Gems.js"
    original = gems.read_text(encoding="utf-8")
    updated = remove_enriched_silicon(original)
    if updated != original:
        gems.write_text(updated, encoding="utf-8")
    shutil.copy2(HERE / "CmiMineralsAndPeat.js", basic.parents[1] / "CmiMineralsAndPeat.js")
    clean_retired_collectible_assets(instance / "kubejs")


def clean_retired_collectible_assets(kubejs):
    assets = kubejs / "assets/cmi/textures/item/material"
    for relative in ("frost_cake_base.png", "parchment/parchment.png",
                     "parchment/torn_parchment_a.png", "parchment/torn_parchment_b.png"):
        (assets / relative).unlink(missing_ok=True)


def remove_enriched_silicon(source):
    updated = ENRICHED_SILICON.sub("", source)
    if 'addNonGemItem("enriched_silicon")' in updated:
        raise ValueError("Unexpected enriched silicon registration")
    return updated


def convert(relative, source, tinkers_namespace):
    source = OLD_TAG.sub(r"\g<1>c:", source)
    source = THERMAL_TAG.sub("", source)
    source = MODEL_CALL.sub(r".modelGenerator(model => Cmi.applyModel(model, \1))", source)
    if relative == "item/Basic.js":
        source = remove_retired_items(source)
        source = re.sub(
            r'(?m)^\t// 蒸汽升级\n(?:\taddItem\("steam_(?:cast_iron|steel)_upgrade"\)\n'
            r'\t\t\.texture\([^\n]+\n\t\t\.tag\([^\n]+\n\n){2}',
            "", source,
        )
        source = re.sub(
            r'(?m)^\t// 热力单元\n\taddItem\("thermal_unit"\)\n\t\t\.texture\([^\n]+\n\n',
            "", source,
        )
        source = re.sub(r'(?m)^\t\t"(basalz|blitz|blizz)",?\n', "", source)
        source = re.sub(
            r'(?m)^\t\taddItem\(\x60\$\{type\}_unit\x60\)\n'
            r'\t\t\t\.texture\([^\n]+\n\n',
            "", source,
        )
        source = source.replace(".glow(true)", '.component("minecraft:enchantment_glint_override", true)')
        source = source.replace(".hunger(20)", ".nutrition(20)")
        source = source.replace('\n\t\t"elite",\n\t\t"elite",', '\n\t\t"elite",')
        source = source.replace("expatternprovider:item/", "extendedae:item/")
        source = re.sub(
            r'(?m)^\t// 升级模板\n\taddMaterial\("drawer_upgrade_template"\)\n\n',
            "", source,
        )
        source = re.sub(
            r'(?m)^\taddMaterial\("platinum_ore_chunk"\)\n(?:\t\t\.(?:texture|tag)\([^\n]+\n)+\n',
            "", source,
        )
        source = re.sub(
            r'(let casingFrame = \[[^\]]*?)\t\t"bronze",\n',
            r'\g<1>',
            source,
        )
    elif relative == "item/Incompletes.js":
        source = re.sub(r'(?m)^\t\t"(?:upgrade_augment_\d+|thermal_mechanism_augment)",?\n', "", source)
        source = re.sub(
            r'(?m)^\t// 热力设备\n\taddItem\("thermal_devices"\)\n\t\t\.parentModel\([^\n]+\n\n',
            "", source,
        )
        source = source.replace("expatternprovider:item/", "extendedae:item/")
    elif relative == "item/Molds.js":
        source = re.sub(
            r'(?ms)^    /\*\*\n(?:     \*[^\n]*\n)*     \*/\n'
            r'    function addClayMold\(name\) \{\n.*?^    \}\n\n',
            "", source,
        )
        source = re.sub(r'(?m)^    addClayMold\("[^"]+"\)\n', "", source)
        source = source.rstrip().removesuffix("})").rstrip() + "\n})\n"
        if "addClayMold" in source:
            raise ValueError("Unexpected clay mold registration")
    elif relative == "item/mechanism/Augment.js":
        source = re.sub(r'(?m)^ +addMechanismAugment\("(?:thermal|reinforced)"\)\n', "", source)
    elif relative == "item/mechanism/Flashdrive.js":
        source = re.sub(
            r'(?m)^[ \t]*"(?:nature|potion|colorful|enchanted|sculk|pig_iron|reinforced|cobalt|wooden|stone|gold|thermal)",?\n',
            "", source,
        )
    elif relative == "material/RawOres.js":
        source = re.sub(r'(?m)^\taddAloneRawMaterial\("(?:ardite|etrium)"\)\n', "", source)
        source = re.sub(r'(?m)^\taddAloneCrushedRawMaterial\("ardite"\)\n', "", source)
    elif relative == "material/Ingots.js":
        source = source.replace('.rarity("extra_green")', '.rarity("uncommon")')
    elif relative == "material/Gems.js":
        source = remove_enriched_silicon(source)
    if "thermal:" in source or ".modelJson(" in source:
        raise ValueError(f"Unsupported dependency or model API in {relative}")
    if relative == "other/Cast.js":
        source = source.replace("tconstruct:casts", f"{tinkers_namespace}:casts")
    return source


def build(source, target, tinkers_namespace):
    (target / "item/mechanism/Random.js").unlink(missing_ok=True)
    if target.parent.name == "startup_scripts":
        clean_retired_collectible_assets(target.parent.parent)
        textures = target.parent.parent / "assets/cmi/textures/item"
        random_textures = textures / "mechanism/random"
        for pattern in ("*.png", "*.png.mcmeta"):
            for texture in random_textures.glob(pattern):
                texture.unlink()
        clay_textures = textures / "material/mold/clay"
        for extension in (".png", ".png.mcmeta"):
            for texture in clay_textures.glob("*" + extension):
                texture.unlink()
            (textures / "framework" / ("bronze" + extension)).unlink(missing_ok=True)
        for extension in (".png", ".png.mcmeta"):
            (textures / "material" / ("drawer_upgrade_template" + extension)).unlink(missing_ok=True)

    for relative in SOURCE_FILES:
        converted = convert(relative, (source / relative).read_text(), tinkers_namespace)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(converted)
    for name in ("Bindings.js", "CmiDeposits.js", "CmiFactoryParts.js", "CmiIndustrialMaterials.js", "CmiLubricant.js",
                 "CmiMechanisms.js", "CmiMineralsAndPeat.js", "CmiMoltenMetals.js",
                 "CmiOilFluids.js", "CmiPolymerMaterials.js", "CmiProcessFluids.js",
                 "CmiSiliconeFluids.js", "CmiSpaceParts.js"):
        shutil.copyfile(HERE / name, target / name)


def install_mechanism_textures(core, assets):
    with ZipFile(core) as jar:
        entries = set(jar.namelist())
        for name in sorted(entries):
            if not re.fullmatch(r"assets/cmi/textures/item/mechanism/(?:complete|incomplete)/(?!thermal)[a-z_]+\.png", name):
                continue
            texture = assets / name.removeprefix("assets/")
            image = jar.read(name)
            if texture.is_file():
                if texture.read_bytes() != image:
                    continue
            else:
                texture.parent.mkdir(parents=True, exist_ok=True)
                texture.write_bytes(image)

            metadata_name = name + ".mcmeta"
            metadata = texture.with_suffix(".png.mcmeta")
            if metadata_name in entries and not metadata.exists():
                metadata.write_bytes(jar.read(metadata_name))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Path to the existing startup_scripts/register directory")
    parser.add_argument("target", type=Path, help="Path to the CMI directory under target startup_scripts")
    parser.add_argument("--tinkers-namespace", choices=("tconstruct", "modernfoundry"), required=True)
    parser.add_argument("--core-art", nargs=2, type=Path, metavar=("CMI_CORE_JAR", "KUBEJS_ASSETS"))
    options = parser.parse_args()
    build(options.source, options.target, options.tinkers_namespace)
    if options.core_art:
        install_mechanism_textures(*options.core_art)
