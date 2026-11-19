ServerEvents.recipes(event => {
  const path = 'expedition:factory/mechanism_equipment/'
  const station = (output, parts, fluid) => {
    const recipe = {
      type: 'neoecoae:integrated_working_station',
      energy: 2000,
      itemOutput: {id: output, count: 1},
      inputItems: parts.map(([ingredient, count]) => ingredient.startsWith('#')
        ? {tag: ingredient.substring(1), count: count || 1}
        : {item: ingredient, count: count || 1})
    }
    if (fluid) recipe.inputFluid = {fluid: fluid[0], amount: fluid[1]}
    event.custom(recipe).id(path + output.replace(':', '/'))
  }

  const ender = ['cmi:ender_mechanism']
  station('ae2:wireless_receiver', [
    ender, ['ae2:fluix_pearl'], ['create:transmitter'], ['#c:plates/iron']
  ])
  station('ae2:spatial_io_port', [ender, ['ae2:io_port'], ['#ae2:glass_cable']])
  station('ae2:spatial_pylon', [
    ender, ['cmi:smart_casing'], ['ae2:fluix_crystal'], ['ae2:fluix_glass_cable']
  ])
  station('aeinfinitybooster:infinity_card', [
    ender, ['ae2:wireless_booster'], ['ae2:fluix_pearl'], ['#c:plates/silicon']
  ])

  const basic = ['cmi:basic_mekanism_mechanism']
  const advanced = ['cmi:advanced_mekanism_mechanism']
  const nuclear = ['cmi:nuclear_mechanism']
  const iron = '#c:plates/industrial_iron'
  const lead = '#c:plates/lead'
  const rubber = ['cmi:silicon_rubber', 200]
  const casing = ['mekanism:steel_casing']

  const basicMachines = [
    ['enrichment_chamber', [['cmi:iron_mechanism'], ['minecraft:packed_ice']]],
    ['crusher', [['cmi:chromeplated_steel_gear', 2], ['minecraft:basalt']]],
    ['energized_smelter', [['cmi:nether_mechanism'], ['minecraft:blaze_rod']]],
    ['precision_sawmill', [['create:mechanical_saw'], ['minecraft:packed_ice']]],
    ['combiner', [['minecraft:piston'], ['mekanism:alloy_infused']]]
  ]
  basicMachines.forEach(([name, parts]) => {
    station('mekanism:' + name, [casing, basic, [iron, 2]].concat(parts), rubber)
  })
  station('mekanism:boiler_valve', [['mekanism:boiler_casing'], basic, [iron]])
  station('mekanism:induction_port', [['mekanism:induction_casing'], basic, [iron]])
  station('mekanismgenerators:turbine_valve', [['mekanismgenerators:turbine_casing'], basic, [iron]])

  const fission = ['mekanismgenerators:fission_reactor_casing']
  station('mekanismgenerators:fission_reactor_port', [fission, advanced, [iron]])
  station('mekanismgenerators:fission_reactor_logic_adapter', [
    fission, advanced, ['mekanism:advanced_control_circuit']
  ])
  station('mekanismgenerators:control_rod_assembly', [
    fission, advanced, nuclear, ['#c:plates/aluminum_alloy'], ['#c:rods/silver', 5], [lead, 4]
  ], rubber)
  station('mekanismgenerators:fission_fuel_assembly', [
    fission, advanced, nuclear, ['#c:plates/aluminum_alloy'], ['mekanism:basic_chemical_tank'], [lead, 4]
  ], ['createdieselgenerators:white_cement', 1000])
})
