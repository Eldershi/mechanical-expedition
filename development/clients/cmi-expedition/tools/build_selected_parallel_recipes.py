"""Extract only user-selected native routes; never edit existing recipe scripts."""
from pathlib import Path
import collections
import hashlib
import io
import json
import re
import tomllib
import zipfile

ROOT = Path(__file__).resolve().parents[3]
CLIENT = ROOT / 'clients/cmi-expedition/instance'
SERVER = ROOT / 'servers/cmi-expedition/instance'
EVIDENCE = ROOT / 'clients/cmi-expedition/evidence/recipe-parallel-20261022'
SELECTION = json.loads((EVIDENCE / 'selection.json').read_text())
RULES = {}

def group(number, rows):
    labels = [r['label'] for r in SELECTION['selected'] if r['section'].startswith(f'## {number:02}｜')]
    values = rows.strip().splitlines()
    assert len(labels) == len(values), (number, len(labels), len(values))
    for label, value in zip(labels, values):
        RULES[label] = {'items': value.strip().split() if value.strip() != '-' else []}

group(1, '''
minecraft:furnace
minecraft:blast_furnace
minecraft:stonecutter
minecraft:paper
minecraft:sugar
minecraft:gunpowder
minecraft:bucket
minecraft:glass_bottle
minecraft:chest
minecraft:hopper
minecraft:repeater
minecraft:comparator
minecraft:piston
minecraft:observer
minecraft:dispenser
minecraft:dropper
minecraft:packed_ice
minecraft:blue_ice
minecraft:glass
''')
group(2, '''
create:andesite_alloy
create:brass_ingot
create:andesite_casing
create:copper_casing
create:brass_casing
create:cogwheel
create:large_cogwheel
create:gearbox create:vertical_gearbox
create:belt_connector
create:fluid_pipe
create:chute
create:whisk
create:propeller
create:brass_hand
create:electron_tube
create:rose_quartz
create:precision_mechanism
create:sail_frame
create:white_sail
create:transmitter
create_connected:control_chip
create:iron_sheet create:copper_sheet create:golden_sheet
''')
group(3, '''
create:water_wheel
create:large_water_wheel
create:windmill_bearing
create:steam_engine
create:flywheel
''')
group(4, '''
create:depot
create:mechanical_press
create:mechanical_mixer
create:encased_fan
create:millstone
create:deployer
create:mechanical_saw
create:mechanical_drill
create:mechanical_bearing
create:mechanical_piston
create:gantry_carriage
create:weighted_ejector
create:mechanical_harvester
create:mechanical_plough
create:mechanical_roller
create:cart_assembler
create:clockwork_bearing
create:elevator_pulley
create:contraption_controls
create:mechanical_arm
create:mechanical_crafter
create:crushing_wheel
createdieselgenerators:basin_lid
createaddition:rolling_mill
vintageimprovements:spring_coiling_machine vintageimprovements:spring_coiling_machine_wheel
''')
group(5, '''
create:fluid_tank
create_connected:fluid_vessel
fluidlogistics:multi_fluid_tank fluidlogistics:horizontal_multi_fluid_tank
fluidlogistics:multi_fluid_access_port
create:spout
cmi:advanced_spout
create:smart_fluid_pipe
create:fluid_valve
create:hose_pulley
create:mechanical_pump fluidlogistics:fluid_pump
fluidlogistics:smart_faucet
fluidlogistics:smart_hopper
fluidlogistics:fluid_transporter fluidlogistics:fluid_hatch
create:item_hatch
create:item_vault
create_connected:item_silo
create:portable_storage_interface
create:portable_fluid_interface
createaddition:portable_energy_interface
create:andesite_funnel
create:andesite_tunnel
create:brass_funnel
create:brass_tunnel
create:smart_chute
create:packager
fluidlogistics:fluid_packager
create:package_frogport
create:stock_link
create:stock_ticker
create:redstone_requester
create:factory_gauge
create_connected:inventory_access_port
create:redstone_link
create:display_link
''')
group(6, '''
create:powered_latch
create:powered_toggle_latch
createaddition:redstone_relay
create:pulse_repeater
create:pulse_extender
create:pulse_timer
create_connected:sequenced_pulse_generator
create:redstone_contact
create:track_station
create:track_signal
create:track_observer
railways:track_switch_brass railways:track_switch_andesite railways:track_coupler
create:controls
railways:fuel_tank railways:portable_fuel_interface
@postbox
create:schedule
create:copper_backtank
create:netherite_backtank
create_jetpack:jetpack create_jetpack:netherite_jetpack
create:wand_of_symmetry
fluidlogistics:hand_pointer
naturescompass:naturescompass
explorerscompass:explorerscompass
''')
group(7, '''
sophisticatedbackpacks:backpack
sophisticatedbackpacks:upgrade_base
sophisticatedbackpacks:stack_upgrade_starter_tier
sophisticatedbackpacks:stack_upgrade_tier_1
sophisticatedbackpacks:stack_upgrade_tier_2
sophisticatedbackpacks:stack_upgrade_tier_3
sophisticatedbackpacks:stack_upgrade_tier_4
@drawers1
@drawers2
@drawers4
functionalstorage:fluid_1
functionalstorage:fluid_2
functionalstorage:fluid_4
functionalstorage:framed_1 functionalstorage:framed_2 functionalstorage:framed_4
functionalstorage:upgrade_template
functionalstorage:iron_downgrade
functionalstorage:copper_upgrade
functionalstorage:gold_upgrade
functionalstorage:diamond_upgrade
functionalstorage:netherite_upgrade
functionalstorage:void_upgrade
functionalstorage:puller_upgrade
functionalstorage:pusher_upgrade
functionalstorage:collector_upgrade
functionalstorage:redstone_upgrade
functionalstorage:configuration_tool functionalstorage:linking_tool
''')
group(8, '''
tconstruct:grout
tconstruct:nether_grout
tconstruct:seared_brick
tconstruct:seared_melter
tconstruct:seared_heater
tconstruct:smeltery_controller
tconstruct:seared_fuel_tank tconstruct:seared_fuel_gauge
tconstruct:seared_ingot_tank tconstruct:seared_ingot_gauge
tconstruct:scorched_alloyer
tconstruct:scorched_fuel_tank tconstruct:scorched_fuel_gauge
tconstruct:scorched_ingot_tank tconstruct:scorched_ingot_gauge
tconstruct:cast_chest
tconstruct:pattern
tconstruct:tinkers_anvil
tconstruct:foundry_controller
create:empty_blaze_burner
create:blaze_burner
createdieselgenerators:burner
create:sturdy_sheet createaddition:diamond_grit cmi:dense_sturdy_sheet
tconstruct:silky_cloth
-
-
-
-
''')
# Copper workstation is the crafting-station casting recipe, not the anvil.
for label, rule in RULES.items():
    if label == '铜工作台': rule['items'] = ['tconstruct:crafting_station']
    if label == '坚固板／致密坚固板': rule['items'] = ['create:sturdy_sheet', 'cmi:dense_sturdy_sheet']
group(9, '''
immersiveengineering:blastbrick
immersiveengineering:blastbrick_reinforced
immersiveengineering:cokebrick
immersiveengineering:coil_lv immersiveengineering:coil_mv immersiveengineering:coil_hv
''')
group(12, '''
ae2:inscriber
ae2:charger
ae2:quartz_fiber
ae2:fluix_glass_cable
@covered_cables
ae2:item_cell_housing
ae2:fluid_cell_housing
appmek:chemical_cell_housing
ae2:cell_component_1k ae2:cell_component_4k ae2:cell_component_16k ae2:cell_component_64k ae2:cell_component_256k
ae2:spatial_cell_component_2 ae2:spatial_cell_component_16 ae2:spatial_cell_component_128
ae2:controller
ae2:drive
ae2:chest
ae2:energy_acceptor
ae2:energy_cell ae2:dense_energy_cell
ae2:terminal
ae2:crafting_terminal
ae2:pattern_encoding_terminal
ae2:pattern_access_terminal
ae2:interface
ae2:pattern_provider
ae2:molecular_assembler
ae2:crafting_unit
ae2:crafting_accelerator
ae2:import_bus
ae2:export_bus
ae2:storage_bus
ae2:toggle_bus
ae2:formation_plane
ae2:annihilation_plane
ae2:formation_core ae2:annihilation_core
ae2:me_p2p_tunnel
ae2:quantum_ring ae2:quantum_link
ae2:spatial_pylon ae2:spatial_io_port
ae2:io_port
ae2:wireless_receiver ae2:wireless_access_point ae2:wireless_booster expatternprovider:wireless_connect expatternprovider:wireless_hub
aeinfinitybooster:infinity_card aeinfinitybooster:dimension_card
ae2:blank_pattern ae2:memory_card ae2:basic_card ae2:advanced_card
ae2:network_tool expatternprovider:wireless_tool expatternprovider:pattern_modifier
ae2:entropy_manipulator ae2:charged_staff ae2:matter_cannon
ae2:condenser
me_beam_former:beam_former_part me_beam_former:beam_former_block me_beam_former:omni_beam_former_block
neoecoae:integrated_working_station
''')
group(15, '\n'.join(['-'] * 14))

FAMILIES = {
 '匠魂熔炼与浇铸原配方整组｜保留当前新增路线': [r'tconstruct:smeltery/(melting|casting)/'],
 '匠魂合金原配方整组': [r'tconstruct:smeltery/alloys/'],
 '匠魂强化原配方整组｜包括被移除的幸运强化路线': [r'tconstruct:tools/modifiers/'],
 '原有熔岩／烈焰血燃料配方': [r'tconstruct:smeltery/melting/fuel/(lava|blaze)$'],
 '原油蒸馏原配方｜含普通与超热蒸馏': [r'createdieselgenerators:distillation/(superheated_)?crude_oil$'],
 '生物柴油原配方': [r'immersiveengineering:refinery/biodiesel$', r'createdieselgenerators:.*biodiesel'],
 '乙醇／生物乙醇原配方': [r'immersiveengineering:fermenter/', r'createaddition:mixing/bioethanol$'],
 '植物油与种子榨油原配方': [r'immersiveengineering:squeezer/.*seed', r'createaddition:compacting/seed_oil$', r'thermal:.*hemp_to_plantoil$'],
 '树脂／乳胶提取原配方': [r'thermal:devices/tree_extractor/'],
 '海水／盐水／卤水／锂相关原配方': [r'mekanism:evaporating/(brine|lithium)$', r'mekanism:.*(salt|brine)'],
 '硫酸／盐酸等已有模组化工原配方': [r'mekanism:chemical_infusing/(hydrogen_chloride|sulfuric_acid|sulfur_trioxide)$', r'immersiveengineering:crafting/redstone_acid$'],
 'AE2 天空石与赛特斯石英相关原加工': [r'ae2:(blasting|smelting|inscriber)/sky_stone', r'create:(milling|crushing)/compat/ae2/', r'ae2:transform/.*(certus|quartz|fluix)'],
 '砂砾／沙／红沙洗涤原配方': [r'create:splashing/(gravel|sand|red_sand)$'],
 '下界岩／黑曜石／凝灰岩粉碎原配方': [r'create:crushing/(netherrack|obsidian|tuff|tuff_recycling)$'],
 '煤／木炭／安山岩等原研磨配方': [r'create:milling/(coal|charcoal|andesite)$'],
 '木材切割与木板批量加工原配方': [r'create:cutting/.*(log|wood|stem|hyphae|planks)', r'farmersdelight:cutting/.*(log|wood|stem|hyphae)'],
 '甘蔗／甜菜相关原加工': [r'minecraft:sugar_from_sugar_cane$', r'create:(milling|pressing)/(sugar_cane|beetroot)$', r'farmersdelight:cutting/sugar_cane'],
 '烈焰蛋糕原有制作路线': [r'create:(filling/blaze_cake|compacting/blaze_cake)$'],
}
for label, patterns in FAMILIES.items():
    assert label in RULES, label
    RULES[label]['ids'] = patterns

def sha(raw): return hashlib.sha256(raw).hexdigest()

def branches(recipe):
    if recipe.get('type') == 'forge:conditional':
        return [leaf for row in recipe['recipes'] for leaf in branches(row['recipe'])]
    return [recipe]

def outputs(recipe):
    found = set()
    for leaf in branches(recipe):
        result = leaf.get('result', leaf.get('results', leaf.get('output', [])))
        if isinstance(result, list): result = result[:1]  # never restore a route for a byproduct
        else: result = [result]
        for value in result:
            if isinstance(value, str): found.add(value)
            elif isinstance(value, dict):
                if isinstance(value.get('item'),str): found.add(value['item'])
                elif value.get('id') and leaf.get('type') == 'ad_astra:nasa_workbench': found.add(value['id'])
    return found

def expanded_items(items, known):
    result = set()
    for item in items:
        if item == '@postbox': result.update(x for x in known if re.fullmatch(r'create:[a-z_]+_postbox',x))
        elif item.startswith('@drawers'):
            n = item[-1]; result.update(x for x in known if re.fullmatch(r'functionalstorage:(oak|spruce|birch|jungle|acacia|dark_oak|mangrove|crimson|warped|cherry|rubberwood)_'+n,x))
        elif item == '@covered_cables': result.update(x for x in known if re.fullmatch(r'ae2:[a-z_]+_(covered|glass|smart|dense_covered|dense_smart)_cable',x))
        else: result.add(item)
    return result

def archives(jar):
    with zipfile.ZipFile(jar) as z:
        yield '', z
        for n in z.namelist():
            if n.startswith('META-INF/jarjar/') and n.endswith('.jar'):
                with zipfile.ZipFile(io.BytesIO(z.read(n))) as nested: yield n,nested

def main():
    rows = []
    jars = sorted((CLIENT/'mods').glob('*.jar')) + list((SERVER/'libraries/net/minecraft/server').glob('*/server-*-extra.jar'))
    for jar in jars:
        for nested,z in archives(jar):
            owners = {'minecraft'} if jar.name.endswith('-extra.jar') else set()
            if 'META-INF/mods.toml' in z.namelist():
                owners.update(x['modId'] for x in tomllib.loads(z.read('META-INF/mods.toml').decode()).get('mods',[]))
            for entry in z.namelist():
                m = re.fullmatch(r'data/([^/]+)/recipes/(.+)\.json',entry)
                if not m or m[1] not in owners: continue
                raw = z.read(entry)
                recipe = json.loads(raw)
                if not isinstance(recipe,dict) or 'type' not in recipe: continue
                rows.append({'nativeId':m[1]+':'+m[2], 'json':recipe, 'outputs':sorted(outputs(recipe)),
                    'source':jar.name+('!'+nested if nested else ''),'sourceEntry':entry,'sourceJsonSha256':sha(raw)})
    known = set().union(*(set(r['outputs']) for r in rows))
    for rule in RULES.values(): rule['items'] = sorted(expanded_items(rule['items'],known))
    selected = {}
    coverage=[]
    for label,rule in RULES.items():
        matched = []
        for row in rows:
            if set(row['outputs']) & set(rule['items']) or any(re.search(p,row['nativeId']) for p in rule.get('ids',[])):
                key=row['nativeId']
                if key in selected: assert selected[key]['json']==row['json'],key
                else: selected[key]=dict(row, id='expedition:selected_native/'+key.replace(':','/'),selections=[])
                if label not in selected[key]['selections']: selected[key]['selections'].append(label)
                matched.append(key)
        coverage.append({'label':label,'rule':rule,'nativeIds':sorted(set(matched)),
            'status':'native_catalog_found' if matched else 'no_native_counterpart_or_needs_review',
            'missingOutputs':sorted(set(rule['items'])-known)})
    catalog={'schemaVersion':1,'mode':'parallel_native_and_cmi',
        'selectionCount':len(SELECTION['selected']),'recipes':sorted(selected.values(),key=lambda r:r['id'])}
    baseline=EVIDENCE/'baseline-summary.json'
    if baseline.exists(): catalog['baselineUnavailable']=json.loads(baseline.read_text())['baselineUnavailable']
    (EVIDENCE/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    (EVIDENCE/'coverage.json').write_text(json.dumps(coverage,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'nativeRecipes':len(selected),'selectedItems':len(coverage),
        'noMatch':[{k:r[k] for k in ['label','missingOutputs']} for r in coverage if not r['nativeIds']],
        'missingOutputs':[{k:r[k] for k in ['label','missingOutputs']} for r in coverage if r['missingOutputs']]},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
