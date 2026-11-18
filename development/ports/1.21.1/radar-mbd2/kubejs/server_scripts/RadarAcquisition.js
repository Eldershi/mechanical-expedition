ServerEvents.tags('item', event => {
  event.add('cmi:batteries', [
    'mekanism:basic_energy_cube', 'mekanism:advanced_energy_cube', 'mekanism:elite_energy_cube',
    'mekanism:ultimate_energy_cube', 'mekanism:creative_energy_cube',
    'createaddition:modular_accumulator', 'createaddition:creative_energy',
    'immersiveengineering:capacitor_lv', 'immersiveengineering:capacitor_mv', 'immersiveengineering:capacitor_hv'
  ])
  event.add('cmi:coils', 'cmi:coil_mechanism')
})

ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const recipePath = 'expedition:radar/acquisition/'
  const sized = (id, count) => id.startsWith('#') ? {tag: id.substring(1), count: count} : {item: id, count: count}
  const station = (output, energy, ingredients, count, fluid) => {
    const recipe = {
      type: 'neoecoae:integrated_working_station',
      energy: energy,
      inputItems: ingredients.map(([item, amount]) => sized(item, amount)),
      itemOutput: {id: 'cmi:' + output, count: count}
    }
    if (fluid) recipe.inputFluid = {fluid: fluid[0], amount: fluid[1]}
    event.custom(recipe).id(recipePath + output)
  }

  for (const alloy of ['stainless_steel', 'aluminum_alloy']) {
    create.pressing('cmi:' + alloy + '_plate', Ingredient.of('#c:ingots/' + alloy))
      .id(recipePath + alloy + '_plate')
  }
  event.shaped('cmi:manyullyn_gear', [' M ', 'M M', ' M '], {M: '#c:ingots/manyullyn'})
    .id(recipePath + 'manyullyn_gear')
  for (const color of ['light_gray', 'white']) {
    create.filling('cmi:' + color + '_reinforced_concrete', [
      'immersiveengineering:steel_scaffolding_standard', Fluid.of('createdieselgenerators:' + color + '_cement', 1000)
    ]).id(recipePath + color + '_reinforced_concrete')
  }

  event.custom({
    type: 'modernfoundry:casting_table',
    id: recipePath + 'glass_rod',
    cast: {tag: 'modernfoundry:casts/multi_use/rod'},
    cast_consumed: false,
    fluid: {fluid: 'modernfoundry:molten_glass', amount: 100},
    cooling_time: 40,
    result: {item: 'cmi:glass_rod'}
  }).id(recipePath + 'glass_rod')
  event.custom({
    type: 'createaddition:rolling',
    ingredients: [{item: 'cmi:glass_rod'}],
    results: [{id: 'cmi:glass_wire', count: 2}]
  }).id(recipePath + 'glass_wire')
  event.shapeless('4x cmi:optical_fiber', [
    '4x cmi:glass_wire', '4x ae2:certus_quartz_dust', 'cmi:silicon_rubber_plate'
  ]).id(recipePath + 'optical_fiber')
  event.custom({
    type: 'ae2:inscriber',
    ingredients: {
      top: {tag: 'c:plates/zinc'},
      middle: {tag: 'c:plates/iron'},
      bottom: {tag: 'c:plates/nickel'}
    },
    mode: 'press',
    result: {id: 'cmi:ferrit_core', count: 4}
  }).id(recipePath + 'ferrit_core')

  vintage.pressurizing(Fluid.of('cmi:molten_etrium', 90), 'ad_astra:etrium_ingot').heated()
    .id(recipePath + 'molten_etrium')
  vintage.pressurizing(Fluid.of('cmi:molten_fluix', 100), 'ae2:fluix_crystal').heated()
    .id(recipePath + 'molten_fluix')
  create.filling('cmi:fluix_wire', ['cmi:optical_fiber', Fluid.of('cmi:molten_fluix', 25)])
    .id(recipePath + 'fluix_wire')

  create.mixing('64x cmi:deposition_catalytic_alloy', [
    Ingredient.of(['#c:ingots/iron', '#c:dusts/iron']),
    Ingredient.of(['#c:ingots/nickel', '#c:dusts/nickel']),
    Ingredient.of(['#c:ingots/cobalt', '#c:dusts/cobalt'])
  ]).superheated().id(recipePath + 'deposition_catalytic_alloy')
  create.cutting('64x cmi:carbon_deposition_catalytic_plate', 'cmi:deposition_catalytic_alloy')
    .id(recipePath + 'carbon_deposition_catalytic_plate')
  create.compacting('cmi:graphene', ['cmi:carbon_deposition_catalytic_plate', 'mekanism:hdpe_pellet'])
    .heated().id(recipePath + 'graphene')
  create.compacting('2x cmi:smart_casing', [
    Ingredient.of('#c:plates/iron'), Ingredient.of('#c:plates/silver'),
    'ae2:charged_certus_quartz_crystal', Ingredient.of('cmi:silicon_rubber'), Fluid.of('cmi:silicon_rubber', 100)
  ]).heated().id(recipePath + 'smart_casing')

  create.compacting('4x cmi:engineering_mechanism_part', [
    Ingredient.of('#c:plates/constantan'), Ingredient.of('#immersiveengineering:circuits/logic'),
    Ingredient.of('#c:gems/dreamcore'), Fluid.of('modernfoundry:molten_signalum', 90)
  ]).heated().id(recipePath + 'engineering_mechanism_part')
  create.compacting('4x cmi:smart_mechanism_augment', [
    Ingredient.of('#c:wires/signalum'), 'ae2:logic_processor', 'ae2:calculation_processor', 'ae2:engineering_processor'
  ]).heated().id(recipePath + 'smart_mechanism_augment')
  const smart = 'cmi:incomplete_smart_mechanism'
  create.sequenced_assembly('cmi:smart_mechanism', Ingredient.of('#c:plates/silver'), [
    vintage.curving(smart, smart).itemAsHead('cmi:mechanism_mold'),
    create.deploying(smart, [smart, 'cmi:smart_mechanism_augment']),
    create.filling(smart, [smart, Fluid.of('immersiveengineering:redstone_acid', 100)]),
    vintage.vacuumizing(smart, smart),
    create.deploying(smart, [smart, 'ae2:fluix_crystal']),
    create.deploying(smart, [smart, 'cmi:engineering_mechanism_part'])
  ]).loops(1).transitionalItem(smart).id(recipePath + 'smart_mechanism')

  station('space_mechanism_part', 1000, [
    ['ae2:singularity', 1], ['ae2:sky_dust', 2], ['#c:gems/dreamcore', 1]
  ], 4, ['cmi:molten_etrium', 90])
  station('aeronautic_mechanism_basement', 2000, [
    ['#c:plates/aluminum_alloy', 2], ['cmi:graphene', 4], ['ad_astra:etrionic_capacitor', 1],
    ['cmi:optical_fiber', 4]
  ], 1, ['cmi:molten_etrium', 90])
  station('aeronautic_mechanism', 16000, [
    ['cmi:aeronautic_mechanism_basement', 1], ['ad_astra:oxygen_gear', 1], ['#c:wires/fluix', 1],
    ['#c:plates/aluminum_alloy', 1], ['cmi:space_mechanism_part', 1]
  ], 1, ['cmi:structural_plastic', 200])

  for (const [component, material] of [
    ['power_supply', '#cmi:batteries'],
    ['transformer', '#cmi:coils'],
    ['tracking_array', 'cmi:aeronautic_mechanism'],
    ['modem', 'cmi:smart_mechanism'],
    ['radar', 'ae2:wireless_receiver']
  ]) {
    station(component, 16000, [['#c:plates/osmium', 4], [material, 1]], 1)
  }
  station('radar_antenna', 16000, [
    ['#c:plates/stainless_steel', 8], ['cmi:optical_fiber', 8], ['cmi:ferrit_core', 4],
    ['ae2:terminal', 1], ['cmi:smart_mechanism', 1]
  ], 1)

  const disk = 'cmi:incomplete_aviation_cell'
  create.sequenced_assembly('cmi:empty_cell', Ingredient.of('#c:plates/aluminum'), [
    create.deploying(disk, [disk, 'cmi:coil_mechanism']),
    create.deploying(disk, [disk, Ingredient.of('#c:gears/manyullyn')]),
    vintage.laser_cutting(disk, disk).energy(4000).maxChargeRate(4000),
    vintage.curving(disk, disk).mode(3)
  ]).loops(1).transitionalItem(disk).id(recipePath + 'empty_cell')
})
