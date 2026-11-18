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
MECHANISMS = ("Augment", "Basement", "Flashdrive", "Parts", "Random")
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
            r'(?m)^\t// 热力单元\n\taddItem\("thermal_unit"\)\n\t\t\.texture\([^\n]+\n\n',
            "", source,
        )
        source = re.sub(r'(?m)^\t\t"(basalz|blitz|blizz)",?\n', "", source)
        source = source.replace(".glow(true)", '.component("minecraft:enchantment_glint_override", true)')
        source = source.replace(".hunger(20)", ".nutrition(20)")
        source = source.replace('\n\t\t"elite",\n\t\t"elite",', '\n\t\t"elite",')
        source = source.replace("expatternprovider:item/", "extendedae:item/")
    elif relative == "item/Incompletes.js":
        source = re.sub(r'(?m)^\t\t"(?:upgrade_augment_\d+|thermal_mechanism_augment)",?\n', "", source)
        source = re.sub(
            r'(?m)^\t// 热力设备\n\taddItem\("thermal_devices"\)\n\t\t\.parentModel\([^\n]+\n\n',
            "", source,
        )
        source = source.replace("expatternprovider:item/", "extendedae:item/")
    elif relative == "item/mechanism/Augment.js":
        source = re.sub(r'(?m)^ +addMechanismAugment\("thermal"\)\n', "", source)
    elif relative == "item/mechanism/Flashdrive.js":
        source = re.sub(r'(?m)^\s*"thermal",\n', "", source)
    elif relative == "material/RawOres.js":
        source = re.sub(r'(?m)^\s*addAloneRawMaterial\("etrium"\)\n', "\n", source)
    elif relative == "material/Ingots.js":
        source = source.replace('.rarity("extra_green")', '.rarity("uncommon")')
    if "thermal:" in source or ".modelJson(" in source:
        raise ValueError(f"Unsupported dependency or model API in {relative}")
    if relative == "other/Cast.js":
        source = source.replace("tconstruct:casts", f"{tinkers_namespace}:casts")
    return source


def build(source, target, tinkers_namespace):
    for relative in SOURCE_FILES:
        converted = convert(relative, (source / relative).read_text(), tinkers_namespace)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(converted)
    for name in ("Bindings.js", "CmiMechanisms.js", "CmiMineralsAndPeat.js", "CmiMoltenMetals.js"):
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
