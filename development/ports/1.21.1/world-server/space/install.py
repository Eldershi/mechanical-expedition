#!/usr/bin/env python3
"""Install matching Earth–Moon and industrial facilities in test instances."""

import argparse
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile

from build_structures import build

HERE = Path(__file__).resolve().parent
INDUSTRY = HERE.parent / "brass-industry"
FACTORY = HERE.parents[1] / "industry"


def update_fuel_quest(instance):
    quests = instance / "config/ftbquests/quests"
    chapter = quests / "chapters/fuel.snbt"
    original = chapter.read_text(encoding="utf-8")
    quest_pattern = re.compile(r'(?ms)^\t\t\{\n(?:(?!^\t\t\}).)*?^\t\t\tid: "7AC1116B656361E6"\n'
                               r'(?:(?!^\t\t\}).)*?^\t\t\}')
    task_item_pattern = re.compile(r'(?ms)(^\t{4}id: "09851817940F4AAE"\n)'
                                   r'\t{4}item: (\{[^\n]+\}|\{\n.*?^\t{4}\})')
    quest = quest_pattern.search(original)
    task = task_item_pattern.search(quest[0]) if quest else None
    if task is None or not any(name in task[2] for name in ('item_tag(cmi:peat_gen)', 'minecraft:dried_kelp_block')):
        raise ValueError("The fuel chapter is missing its expected peat or dried kelp task")
    updated = task_item_pattern.sub(r'\g<1>\t\t\t\titem: { count: 1, id: "minecraft:dried_kelp_block" }', quest[0])
    updated = re.sub(r'(?m)^(\t{3}icon: )"cmi:peat"$', r'\g<1>"minecraft:dried_kelp_block"', updated)
    updated = re.sub(r'(?m)^(\t{3}description: ).+$', r'\g<1>["烧制海带，再以九片干海带合成可作燃料的干海带块。"]', updated)
    updated = re.sub(r'(?m)^(\t{3}subtitle: ).+$', r'\g<1>"可再生的块状燃料"', updated)
    updated = re.sub(r'(?m)^(\t{3,4}title: )"泥炭"$', r'\g<1>"干海带块"', updated)
    chapter.write_text(original[:quest.start()] + updated + original[quest.end():], encoding="utf-8")

    for name in ("en_us", "zh_cn"):
        language = quests / "lang" / f"{name}.snbt"
        if not language.is_file():
            continue
        original = language.read_text(encoding="utf-8")
        if name == "zh_cn" or re.search(r"[\u4e00-\u9fff]", original):
            title = "干海带块"
            subtitle = "可再生的块状燃料"
            description = "烧制海带，再以九片干海带合成可作燃料的干海带块。"
        else:
            title = "Dried Kelp Block"
            subtitle = "Renewable fuel"
            description = "Smelt kelp and craft nine dried kelp into a fuel block."
        for key, value in (
            ("task.09851817940F4AAE.title", f'"{title}"'),
            ("quest.7AC1116B656361E6.title", f'"{title}"'),
            ("quest.7AC1116B656361E6.quest_subtitle", f'"{subtitle}"'),
            ("quest.7AC1116B656361E6.quest_desc", f'["{description}"]'),
        ):
            original = re.sub(rf"(?m)^(\s*{re.escape(key)}: ).+$", lambda match: match[1] + value, original)
        language.write_text(original, encoding="utf-8")


def install(client, server, java):
    if not (client / "mods/adastra-1.21.1-1.16.26-neoforge.jar").is_file():
        raise ValueError("Client does not match the 1.21.1 space baseline")
    if not (server / "libraries/net/neoforged/neoforge/21.1.267/unix_args.txt").is_file():
        raise ValueError("Server does not match NeoForge 21.1.267")
    if not (server / "mods/adastra-1.21.1-1.16.26-neoforge.jar").is_file():
        raise ValueError("Server does not match the 1.21.1 space baseline")
    materials = FACTORY.parent / "cmi-materials"
    retire_items = runpy.run_path(str(materials / "build_registrations.py"))["retire_items"]
    with tempfile.TemporaryDirectory() as directory:
        staged = Path(directory)
        overlay = staged / "overlay"
        build(overlay)
        shutil.copytree(HERE / "overlay", overlay, dirs_exist_ok=True)
        subprocess.run([sys.executable, str(INDUSTRY / "build.py"), str(overlay)], check=True)
        shutil.copytree(INDUSTRY / "overlay", overlay, dirs_exist_ok=True)
        vanilla, = server.glob("libraries/net/minecraft/server/1.21.1-*/*-extra.jar")
        subprocess.run([sys.executable, str(HERE.parent / "deposits/build_deposits.py"),
                        str(HERE.parents[4] / "pack/kubejs"), str(overlay / "kubejs"),
                        str(vanilla)], check=True)
        for path in (
            "kubejs/server_scripts/ExpeditionNetherProgression.js",
            "kubejs/startup_scripts/ExpeditionSugarSyrup.js",
            "kubejs/server_scripts/ExpeditionSyrupRecipes.js",
            "kubejs/server_scripts/ExpeditionPlantAsh.js",
            "kubejs/server_scripts/ExpeditionLunarSilicon.js",
            "kubejs/server_scripts/ExpeditionMineralChemistry.js",
            "kubejs/server_scripts/ExpeditionVanadium.js",
            "kubejs/server_scripts/ExpeditionSeaWater.js",
            "kubejs/server_scripts/ExpeditionWasteProcessing.js",
            "kubejs/data/expedition/recipe/factory/space/press_single_crystal_silicon.json",
            "kubejs/data/createcraftedbeginning/tags/item/press_head_tools.json",
            "kubejs/client_scripts/ExpeditionSugarSyrupLanguage.js",
            "kubejs/client_scripts/ExpeditionMineralChemistryLanguage.js",
        ):
            target = overlay / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(FACTORY / path, target)
        registrations = overlay / "kubejs/startup_scripts/cmi"
        registrations.mkdir(parents=True, exist_ok=True)
        shutil.copy2(materials / "CmiProcessFluids.js", registrations)
        shutil.copy2(materials / "CmiIndustrialMaterials.js", registrations)
        shutil.copy2(materials / "CmiDeposits.js", registrations)
        subprocess.run([sys.executable, str(HERE.parent / "build.py"), "--java", str(java),
                        "--server", str(server), "--output", str(staged), "space"], check=True)
        adapter, = staged.glob("*.jar")
        with ZipFile(adapter) as archive:
            if b"expedition_space_acceptance" in archive.read("META-INF/neoforge.mods.toml"):
                raise ValueError("Acceptance mod may only be installed in a disposable verification instance")
        for instance in (client, server):
            subprocess.run([sys.executable, str(FACTORY / "update_nether_quests.py"),
                            str(instance / "config/ftbquests/quests")], check=True)
            update_fuel_quest(instance)
            retire_items(instance)
            shutil.copytree(overlay, instance, dirs_exist_ok=True)
            shutil.copy2(adapter, instance / "mods")
        client_scripts = client / "kubejs/client_scripts"
        client_scripts.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FACTORY / "kubejs/client_scripts/ExpeditionMechanismLanguage.js", client_scripts)
        subprocess.run([sys.executable, str(FACTORY / "seared-materials/install.py"),
                        "--client", str(client), "--server", str(server)], check=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--java", type=Path, required=True)
    options = parser.parse_args()
    install(options.client.resolve(), options.server.resolve(), options.java.resolve())
