// priority: -1250
// Keep established low-cost routes when merging upstream 77f6e7a.
// Independent IDs leave the upstream recipes and restored native catalogs intact.
ServerEvents.recipes(event => {
  let { create, vintageimprovements, thermal, thermal_extra, immersiveengineering, mekanism, kubejs } = event.getRecipes()
  const PREFIX = 'expedition:upstream_compat/'

  // The old iron-plate light mechanism remains available, but installs its
  // distinguishing component before pressing so it cannot collide with COIL.
  let light = Mechanisms.LIGHT.INC
  create.sequenced_assembly(Mechanisms.LIGHT.COM, '#forge:plates/iron', [
    create.deploying(light, [light, Mechanisms.LIGHT.AUG]),
    vintageimprovements.curving(light, light).itemAsHead('cmi:mechanism_mold'),
    create.filling(light, [light, Fluid.of('immersiveengineering:creosote', 100)]),
    vintageimprovements.vacuumizing(light, light),
    create.deploying(light, [light, '#forge:rods/constantan']),
    create.deploying(light, [light, Mechanisms.PART.ENGIN])
  ]).transitionalItem(light).loops(1).id(PREFIX + 'light_mechanism_iron_plate')

  thermal_extra.component_assembly(Mechanisms.LIGHT.COM, [
    Fluid.of('immersiveengineering:creosote', 100),
    '#forge:plates/iron', Mechanisms.LIGHT.AUG,
    '#forge:rods/constantan', Mechanisms.PART.ENGIN
  ]).id(PREFIX + 'light_mechanism_assembly_iron_plate')

  // Same materials as the previous CMI devices, yielding their new equivalents.
  kubejs.shaped('steam_letters:advanced_spout', ['ABA', 'CDC', ' E '], {
    A: ['#forge:ingots/cast_iron', '#forge:plates/cast_iron'],
    B: 'vintageimprovements:redstone_module', C: Mechanisms.COPPER.COM,
    D: 'create:spout', E: 'thermal:cured_rubber'
  }).id(PREFIX + 'advanced_spout_cast_iron')

  kubejs.shaped('steam_letters:steam_hammer', ['PCP', 'MGM', ' X '], {
    P: '#forge:plates/bronze', M: Mechanisms.STEAM.COM,
    C: Casing.BRONZE, G: 'create:mechanical_press', X: '#forge:storage_blocks/bronze'
  }).id(PREFIX + 'steam_hammer_previous_materials')

  // Legacy steam mods stay installed for old-world compatibility. Their native
  // crafts may have different prices, so keep the established CMI crafts too.
  ;[
    {metal: 'bronze', masonry: 'tconstruct:seared_bricks'},
    {metal: 'cast_iron', masonry: 'tconstruct:scorched_bricks'},
    {metal: 'steel', masonry: 'immersiveengineering:blastbrick'}
  ].forEach(material => {
    let metal = material.metal
    let plate = '#forge:plates/' + metal
    let ingot = '#forge:ingots/' + metal
    let casing = ['cmi:bronze_casing', 'steam_letters:bronze_casing']
    kubejs.shaped('steampowered:' + metal + '_boiler', ['AAA', 'ACA', 'ABA'], {
      A: [plate, ingot], B: 'create:fluid_pipe', C: 'create:fluid_tank'
    }).id(PREFIX + 'legacy_steam/' + metal + '_boiler')
    kubejs.shaped('steampowered:' + metal + '_burner', ['AAA', 'ABA', 'CCC'], {
      A: [plate, ingot], B: Mechanisms.STONE.COM, C: material.masonry
    }).id(PREFIX + 'legacy_steam/' + metal + '_burner')
    kubejs.shaped('steampowered:' + metal + '_steam_engine', ['ABE', 'MCF', 'ABE'], {
      A: plate, B: ingot, C: casing, M: Mechanisms.STEAM.COM,
      E: 'create:andesite_alloy', F: 'create:shaft'
    }).id(PREFIX + 'legacy_steam/' + metal + '_steam_engine')
    kubejs.shaped('steampowered:' + metal + '_flywheel', ['AB ', 'CFB', 'AB '], {
      A: 'createdieselgenerators:engine_piston', B: plate,
      C: casing, F: 'create:flywheel'
    }).id(PREFIX + 'legacy_steam/' + metal + '_flywheel')
  })
  kubejs.shaped('cmi:bronze_solar_boiler', ['ABA', 'ACA', 'DDD'], {
    A: ['#forge:plates/bronze', '#forge:ingots/bronze'], B: '#forge:plates/silver',
    C: Mechanisms.STEAM.COM, D: 'tconstruct:seared_bricks'
  }).id(PREFIX + 'legacy_steam/bronze_solar_boiler')
  kubejs.shaped('cmi:bronze_fluid_burner', ['AAA', 'ABA', 'CCC'], {
    A: ['#forge:plates/bronze', '#forge:ingots/bronze'],
    B: Mechanisms.COPPER.COM, C: 'tconstruct:seared_bricks'
  }).id(PREFIX + 'legacy_steam/bronze_fluid_burner')

  // The former available tablet craft is retained alongside the upstream assembler.
  event.custom({
    type: 'minecraft:crafting_shaped',
    key: {
      A: { tag: 'mekanism:alloys/infused' },
      I: { tag: 'forge:ingots/gold' },
      R: { tag: 'forge:dusts/redstone' }
    },
    pattern: ['RIR', 'AIA', 'RIR'],
    result: { item: 'mekanism:energy_tablet' }
  }).id(PREFIX + 'energy_tablet_previous_native')

  // Keep the old sugar-fed syrup variants; plain-cane/beetroot yields improve upstream.
  create.compacting([Fluid.of('thermal:syrup', 150), 'cmi:sugarcane_fiber'], [
    'minecraft:sugar_cane', 'minecraft:sugar'
  ]).id(PREFIX + 'syrup_cane_with_sugar')
  create.compacting(Fluid.of('thermal:syrup', 100), [
    '#forge:vegetables/beetroot', 'minecraft:sugar'
  ]).id(PREFIX + 'syrup_beetroot_with_sugar')

  // Upstream's metal-file reorganisation removes these existing ore/raw routes.
  // Restore concrete unified outputs after the generic removals, before the
  // selected-native script takes its immutable retained-recipe snapshot.
  CmiMetal.getAll().forEach(material => {
    let metal = String(material.getId())
    let dust = '#forge:dusts/' + metal
    let ingot = '#forge:ingots/' + metal
    let raw = '#forge:raw_materials/' + metal
    let ore = '#forge:ores/' + metal
    let rawBlock = '#forge:storage_blocks/raw_' + metal
    if (!Ingredient.isNotNull(dust)) return
    let out = highPriorityItem(dust)
    if (Ingredient.isNotNull(ingot)) {
      thermal.pulverizer(out, [ingot]).energy(2000)
        .id(PREFIX + 'metal/' + metal + '/thermal_ingot')
      immersiveengineering.crusher(out).secondaries([]).input(ingot)
        .id(PREFIX + 'metal/' + metal + '/ie_ingot')
    }
    if (Ingredient.isNotNull(raw)) {
      thermal.pulverizer(Item.of(Ingredient.getFirstItemId(dust)).withChance(1.25), [raw])
        .id(PREFIX + 'metal/' + metal + '/thermal_raw')
      immersiveengineering.crusher(out, raw)
        .secondaries(Item.of(Ingredient.getFirstItemId(dust)).withChance(1 / 3))
        .id(PREFIX + 'metal/' + metal + '/ie_raw')
    }
    if (Ingredient.isNotNull(ore)) {
      thermal.pulverizer(highPriorityItem(dust, 2), [ore])
        .id(PREFIX + 'metal/' + metal + '/thermal_ore')
      immersiveengineering.crusher(highPriorityItem(dust, 2)).secondaries([]).input(ore)
        .id(PREFIX + 'metal/' + metal + '/ie_ore')
    }
    if (Ingredient.isNotNull(rawBlock)) {
      immersiveengineering.crusher(highPriorityItem(dust, 12)).secondaries([]).input(rawBlock)
        .id(PREFIX + 'metal/' + metal + '/ie_raw_block')
    }
  })

  // Explicit, one-way recovery for inventories/tanks containing pre-merge IDs.
  kubejs.shapeless('cmi:basalz_general_component', ['cmi:basalt_general_component'])
    .id(PREFIX + 'basalt_component_to_basalz')
  kubejs.shapeless('steam_letters:bronze_casing', ['cmi:bronze_casing'])
    .id(PREFIX + 'legacy_bronze_casing')
  kubejs.shapeless('cmi:bronze_casing', ['steam_letters:bronze_casing'])
    .id(PREFIX + 'new_bronze_casing_to_legacy')
  create.mixing(Fluid.of('cmi:hydrogen_oxygen_fuel', 1000), [
    Fluid.of('neoecoae:cryotheum_solution', 1000)
  ]).id(PREFIX + 'old_cryo_fuel_to_hydrogen_oxygen')
  mekanism.centrifuging(
    MekType.Gas.of('cmi:nuke_waste', 100),
    MekType.Gas.of('mekanism:nuclear_waste', 100)
  ).id(PREFIX + 'legacy_nuclear_waste_gas')
  mekanism.centrifuging(
    MekType.Gas.of('cmi:spent_nuke_waste', 100),
    MekType.Gas.of('mekanism:spent_nuclear_waste', 100)
  ).id(PREFIX + 'legacy_spent_waste_gas')
})
