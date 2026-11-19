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


def convert(relative, source, tinkers_namespace):
    source = OLD_TAG.sub(r"\g<1>c:", source)
    source = THERMAL_TAG.sub("", source)
    source = MODEL_CALL.sub(r".modelGenerator(model => Cmi.applyModel(model, \1))", source)
    if relative == "item/Basic.js":
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
    if "thermal:" in source or ".modelJson(" in source:
        raise ValueError(f"Unsupported dependency or model API in {relative}")
    if relative == "other/Cast.js":
        source = source.replace("tconstruct:casts", f"{tinkers_namespace}:casts")
    return source


def build(source, target, tinkers_namespace):
    (target / "item/mechanism/Random.js").unlink(missing_ok=True)
    if target.parent.name == "startup_scripts":
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
    for name in ("Bindings.js", "CmiFactoryParts.js", "CmiIndustrialMaterials.js", "CmiLubricant.js",
                 "CmiMechanisms.js", "CmiMineralsAndPeat.js", "CmiMoltenMetals.js",
                 "CmiOilFluids.js", "CmiPolymerMaterials.js", "CmiProcessFluids.js",
                 "CmiSiliconeFluids.js", "CmiSpaceParts.js"):
        shutil.copyfile(HERE / name, target / name)


def install_mechanism_textures(core, assets):
    with ZipFile(core) as jar:
        for name in jar.namelist():
            if re.fullmatch(r"assets/cmi/textures/item/mechanism/(?:complete|incomplete)/(?!thermal)[a-z_]+\.png", name):
                file = assets / name.removeprefix("assets/")
                if not file.exists():
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(jar.read(name))


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
