ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/control/'
  const item = id => id.startsWith('#') ? {tag: id.substring(1)} : {item: id}
  const inscribe = (output, middle, top, bottom, mode) => {
    const ingredients = {middle: item(middle), top: item(top)}
    if (bottom) ingredients.bottom = item(bottom)
    event.custom({type: 'ae2:inscriber', ingredients: ingredients, mode: mode, result: {id: output}})
      .id(path + output.replace(':', '/'))
  }
  const station = (id, energy, fluid, amount, parts, count) => {
    event.custom({
      type: 'neoecoae:integrated_working_station', energy: energy,
      itemOutput: {id: 'cmi:' + id, count: count},
      inputFluid: {fluid: fluid, amount: amount},
      inputItems: parts.map(([ingredient, quantity]) => Object.assign(item(ingredient), {count: quantity}))
    }).id(path + id)
  }
  const assembleMechanism = (mechanism, [firstPart, secondPart, thirdPart, finalPart], fluid, amount) => {
    const incomplete = 'cmi:incomplete_' + mechanism
    create.sequenced_assembly('cmi:' + mechanism, 'cmi:' + mechanism + '_basement', [
      create.deploying(incomplete, [incomplete, firstPart]),
      create.deploying(incomplete, [incomplete, secondPart]),
      vintage.laser_cutting(incomplete, incomplete).energy(1000).maxChargeRate(100),
      create.filling(incomplete, [incomplete, Fluid.of(fluid, amount)]),
      create.deploying(incomplete, [incomplete, thirdPart]),
      create.deploying(incomplete, [incomplete, finalPart])
    ]).transitionalItem(incomplete).loops(1).id(path + 'sequenced_' + mechanism)
  }
  event.custom({
    type: 'mekanism:metallurgic_infusing', item_input: {item: 'ae2:silicon'},
    chemical_input: {amount: 20, tag: 'mekanism:carbon'}, output: {id: 'cmi:silicon_carbide'}
  }).id(path + 'silicon_carbide')
  inscribe('cmi:silicon_carbide_plate', 'cmi:silicon_carbide', 'ae2:silicon_press', null, 'inscribe')
  inscribe('cmi:inscribed_silicon', 'ae2:printed_silicon', 'vintageimprovements:signalum_wire', null, 'press')
  inscribe('cmi:printed_concurrent_processor', 'cmi:silicon_carbide_plate', 'cmi:concurrent_processor_press', null, 'inscribe')
  inscribe('cmi:concurrent_processor', 'cmi:silicon_carbide', 'cmi:inscribed_silicon', 'cmi:printed_concurrent_processor', 'press')
  create.mechanical_crafting('cmi:concurrent_processor_press', ['P E', ' S ', 'E P'], {
    P: 'cmi:silicon_carbide_plate', E: 'ae2:engineering_processor', S: 'ae2:silicon_press'
  }).id(path + 'concurrent_processor_press')
  create.mixing('cmi:cobalt_electrolyte', [
    'vintageimprovements:cobalt_sheet', Fluid.of('immersiveengineering:redstone_acid', 100)
  ]).id(path + 'cobalt_electrolyte')
  create.mixing('cmi:enriched_alloy', [Ingredient.of('#c:ingots/aluminum'), 'cmi:cobalt_electrolyte'])
    .heated().id(path + 'enriched_alloy')
  create.filling('cmi:enriched_osmium_crystal', [
    'cmi:pure_semi_molten_osmium', Fluid.of('minecraft:water', 1000)
  ]).id(path + 'enriched_osmium_crystal')
  create.cutting('cmi:osmium_wafer', 'cmi:enriched_osmium_crystal').id(path + 'osmium_wafer')
  create.cutting('cmi:silicon_wafer', 'ae2:silicon').id(path + 'silicon_wafer')
  for (const [suffix, input] of [['silicon', 'ae2:silicon'], ['single_crystal', 'cmi:single_crystal_silicon']]) {
    event.custom({
      type: 'extendedae:circuit_cutter',
      input: {ingredient: {item: input}},
      output: {id: 'cmi:silicon_wafer', count: 1}
    }).id(path + 'silicon_wafer_circuit_cutter_' + suffix)
  }
  create.cutting('cmi:germanium_wafer', 'cmi:germanium_crystal').id(path + 'germanium_wafer')
  create.cutting('cmi:entro_alloy_wafer', 'cmi:entro_alloy').id(path + 'entro_alloy_wafer')
  event.recipes.vintageimprovements.laser_cutting('cmi:ionized_red_dust', 'ad_astra:mars_sand')
    .energy(1000).maxChargeRate(1000).id(path + 'ionized_red_dust')
  create.mixing('cmi:germanium_mixture', [
    'cmi:ionized_red_dust', Ingredient.of('#c:dusts/zinc'), Fluid.of('mekanism:sulfuric_acid', 100)
  ]).heated().id(path + 'germanium_mixture')
  create.mixing('cmi:germanium_crystal', [
    'cmi:germanium_mixture', 'cmi:silicon_carbide', Fluid.of('neoecoae:cryotheum_solution', 100)
  ]).superheated().id(path + 'germanium_crystal')
  station('mekanism_mechanism_part', 1000, 'modernfoundry:molten_cobalt', 180, [
    ['#c:plates/osmium', 1], ['cmi:chromeplated_steel_gear', 1], ['#c:gems/dreamcore', 1]
  ], 4)
  const tiers = [
    ['basic', 'cmi:enriched_alloy', 'cmi:osmium_wafer'],
    ['advanced', 'mekanism:alloy_infused', 'cmi:silicon_wafer'],
    ['elite', 'mekanism:alloy_reinforced', 'cmi:germanium_wafer'],
    ['ultimate', 'mekanism:alloy_atomic', 'cmi:entro_alloy_wafer']
  ]
  tiers.forEach(([tier, alloy, wafer]) => {
    const electronics = 'cmi:' + tier + '_electronic_components'
    const mechanism = tier + '_mekanism_mechanism'
    const circuit = 'mekanism:' + tier + '_control_circuit'
    inscribe(electronics, wafer, alloy, '#c:plates/copper', 'press')
    inscribe(circuit, 'neoecoae:crystal_matrix', 'cmi:silicon_carbide_plate', electronics, 'press')
    station(mechanism + '_basement', 2000, 'cmi:silicon_rubber', 100, [
      ['#c:plates/stainless_steel', 2], [alloy, 1], [electronics, 1], ['cmi:optical_fiber', 4]
    ], 1)
    assembleMechanism(mechanism, [
      circuit, 'cmi:chromeplated_steel_gear', 'cmi:silicon_rubber_plate', 'cmi:mekanism_mechanism_part'
    ], 'immersiveengineering:redstone_acid', 200)
  })
  station('computing_mechanism_basement', 2000, 'immersiveengineering:redstone_acid', 100, [
    ['cmi:silicon_carbide_plate', 2], ['cmi:silicon_rubber_plate', 1],
    ['#c:plates/platinum', 2], ['cmi:fluix_wire', 4]
  ], 1)
  assembleMechanism('computing_mechanism', [
    'cmi:concurrent_processor', 'neoecoae:superconducting_processor', 'cmi:nuke_cooler', 'cmi:mekanism_mechanism_part'
  ], 'cmi:structural_plastic', 200)
  station('titanium_alloy_coil', 2000, 'cmi:silicon_rubber', 100, [
    ['cmi:titanium_alloy_plate', 1], ['cmi:fluix_wire', 8]
  ], 1)
  station('antimatter_mechanism_basement', 2000, 'neoecoae:cryotheum_solution', 90, [
    ['cmi:titanium_alloy_plate', 2], ['alexscaves:azure_neodymium_ingot', 1],
    ['#c:plates/refined_obsidian', 1], ['extendedae_plus:oblivion_singularity', 1]
  ], 1)
  assembleMechanism('antimatter_mechanism', [
    'mekanism:pellet_plutonium', 'mekanism:pellet_polonium', 'cmi:titanium_alloy_coil', 'cmi:quantum_mechanism_part'
  ], 'cmi:ferrouslime', 250)
})
