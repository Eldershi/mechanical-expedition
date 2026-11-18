ServerEvents.tags('item', event => {
  event.add('c:plates/carbon_polymerization_catalytic', 'cmi:carbon_polymerization_catalytic_plate')
  event.add('cmi:mercury_stones', ['ad_astra:mercury_stone', 'ad_astra:mercury_cobblestone'])
})

ServerEvents.recipes(event => {
  const create = event.recipes.create
  const path = 'expedition:factory/space/'
  const station = (id, output, energy, parts, fluid, amount) => {
    const recipe = {
      type: 'neoecoae:integrated_working_station',
      energy: energy,
      itemOutput: {id: output, count: 1},
      inputItems: parts.map(([item, count]) => item.startsWith('#')
        ? {tag: item.substring(1), count: count} : {item: item, count: count})
    }
    if (fluid) recipe.inputFluid = {fluid: fluid, amount: amount}
    event.custom(recipe).id(path + id)
  }

  event.blasting('cmi:titanium_ingot', 'cmi:raw_titanium').xp(0.7).id(path + 'titanium_ingot')
  event.blasting('ad_astra:etrium_ingot', 'cmi:raw_etrium').xp(0.7).id(path + 'etrium_ingot')
  create.milling('cmi:etrium_dust', 'ad_astra:etrium_ingot').id(path + 'etrium_dust')
  create.mixing('cmi:titanium_alloy_ingot', [
    Ingredient.of('#c:ingots/titanium'), Ingredient.of('#c:ingots/chromium')
  ]).superheated().id(path + 'titanium_alloy')
  for (const [plate, source] of [
    ['titanium', 'cmi:titanium_ingot'], ['titanium_alloy', 'cmi:titanium_alloy_ingot'],
    ['tungsten', 'neoecoae:tungsten_ingot'], ['superconducting_mercury', 'cmi:superconducting_mercury_ingot']
  ]) {
    create.pressing(`cmi:${plate}_plate`, source).id(path + plate + '_plate')
  }
  create.compacting('2x cmi:titanium_alloy_mesh', [
    'cmi:titanium_alloy_plate', Ingredient.of('#c:wires/aluminum')
  ]).heated().id(path + 'titanium_alloy_mesh')

  event.custom({
    type: 'mekanism:metallurgic_infusing',
    item_input: {item: 'cmi:tungsten_plate'},
    chemical_input: {amount: 20, tag: 'mekanism:carbon'},
    output: {id: 'cmi:tungsten_steel_plate'}
  }).id(path + 'tungsten_steel_plate')
  station('incomplete_tungsten_steel_plate', 'cmi:incomplete_tungsten_steel_plate', 2000, [
    ['#c:plates/tungsten', 1], ['cmi:titanium_alloy_mesh', 1], ['#c:plates/aluminum_alloy', 1]
  ], 'immersiveengineering:redstone_acid', 100)
  event.custom({
    type: 'mekanism:combining',
    main_input: {item: 'cmi:incomplete_tungsten_steel_plate'},
    extra_input: {item: 'cmi:tungsten_steel_plate'},
    output: {id: 'cmi:composite_tungsten_steel_plate'}
  }).id(path + 'composite_tungsten_steel_plate')

  station('carbon_polymerization_catalytic_plate', 'cmi:carbon_polymerization_catalytic_plate', 2000, [
    ['cmi:titanium_alloy_mesh', 1], ['#c:wires/aluminum', 1]
  ], 'modernfoundry:molten_chromium', 45)
  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: {tag: 'c:plates/carbon_polymerization_catalytic'},
    energy: 120,
    input0: {fluid: 'cmi:light_olefin', amount: 500},
    result: {id: 'cmi:polymeric_carbon_solution', amount: 50}
  }).id(path + 'polymeric_carbon_solution')
  create.compacting('cmi:incomplete_carbon_nanotube', [
    'cmi:graphene', Fluid.of('cmi:polymeric_carbon_solution', 50)
  ]).id(path + 'incomplete_carbon_nanotube')
  event.custom({
    type: 'mekanism:metallurgic_infusing',
    item_input: {item: 'cmi:incomplete_carbon_nanotube'},
    chemical_input: {amount: 20, tag: 'mekanism:carbon'},
    output: {id: 'cmi:carbon_nanotube'}
  }).id(path + 'carbon_nanotube')
  station('incomplete_composite_carbon_fiber_plate', 'cmi:incomplete_composite_carbon_fiber_plate', 2000, [
    ['cmi:composite_tungsten_steel_plate', 1], ['cmi:carbon_nanotube', 4]
  ], 'cmi:structural_plastic', 50)
  create.compacting('cmi:composite_carbon_fiber_plate', [
    'cmi:incomplete_composite_carbon_fiber_plate', Ingredient.of('#c:plates/osmium')
  ]).heated().id(path + 'composite_carbon_fiber_plate')

  const mercuryReaction = (id, item, product) => {
    const recipe = {
      type: 'mekanism:reaction',
      duration: 60,
      energy_required: 12000,
      item_input: {tag: item, count: 1},
      chemical_input: {chemical: 'mekanism:steam', amount: 50},
      fluid_input: {fluid: 'mekanism:sulfuric_acid', amount: 50},
      chemical_output: {id: 'cmi:mercury_mixture', amount: 10}
    }
    if (product) recipe.item_output = {id: product, count: 1}
    event.custom(recipe).id(path + id)
  }
  mercuryReaction('acid_washed_mercury_rock', 'cmi:mercury_stones', 'cmi:acid_washed_mercury_rock')
  mercuryReaction('mercury_mixture_from_cinnabar', 'c:dusts/cinnabar')
  create.mixing('cmi:raw_titanium_mixture', ['cmi:raw_titanium', Ingredient.of('#c:dusts/aluminum')])
    .superheated().id(path + 'raw_titanium_mixture')
  event.custom({
    type: 'mekanism:oxidizing',
    input: {item: 'cmi:raw_titanium_mixture'},
    output: {id: 'cmi:titanium_oxide', amount: 10}
  }).id(path + 'titanium_oxide')
  event.custom({
    type: 'mekanism:chemical_infusing',
    left_input: {chemical: 'cmi:mercury_mixture', amount: 1},
    right_input: {chemical: 'cmi:titanium_oxide', amount: 1},
    output: {id: 'cmi:overheated_mercury_mixture', amount: 2}
  }).id(path + 'overheated_mercury_mixture')
  event.custom({
    type: 'mekanism:reaction',
    duration: 60,
    energy_required: 12000,
    item_input: {tag: 'c:ingots/silver', count: 1},
    chemical_input: {chemical: 'cmi:overheated_mercury_mixture', amount: 100},
    fluid_input: {fluid: 'cmi:molten_etrium', amount: 90},
    item_output: {id: 'cmi:superconducting_mercury_ingot', count: 1},
    chemical_output: {id: 'mekanism:sulfur_trioxide', amount: 100}
  }).id(path + 'superconducting_mercury_ingot_from_mixture')
  station('superconducting_mercury_ingot', 'cmi:superconducting_mercury_ingot', 4000, [
    ['#c:ingots/silver', 1], ['cmi:acid_washed_mercury_rock', 1], ['#c:plates/titanium', 1]
  ], 'cmi:molten_etrium', 90)
  create.mixing(Fluid.of('cmi:ferrouslime', 250), [
    'alexscaves:ferrouslime_ball'
  ]).heated().id(path + 'ferrouslime')
  create.mixing(Fluid.of('cmi:composite_magnetic_fluid', 100), [
    'cmi:etrium_dust', 'cmi:etrium_dust',
    Fluid.of('cmi:ferrouslime', 50)
  ]).heated().id(path + 'composite_magnetic_fluid')
  station('composite_magnetic_conduction_plate', 'cmi:composite_magnetic_conduction_plate', 114514, [
    ['cmi:superconducting_mercury_plate', 1]
  ], 'cmi:composite_magnetic_fluid', 100)

  const cooler = 'cmi:incomplete_nuke_cooler'
  create.sequenced_assembly('cmi:nuke_cooler', Ingredient.of('#c:plates/stainless_steel'), [
    create.deploying(cooler, [cooler, 'alexscaves:polymer_plate']),
    create.deploying(cooler, [cooler, Ingredient.of('#c:plates/platinum')]),
    create.deploying(cooler, [cooler, 'mekanism:structural_glass'])
  ]).transitionalItem(cooler).loops(1).id(path + 'nuke_cooler')
  station('astronautic_mechanism_basement', 'cmi:astronautic_mechanism_basement', 2000, [
    ['#c:plates/titanium', 2], ['cmi:carbon_nanotube', 4], ['ad_astra:etrionic_capacitor', 1],
    ['cmi:optical_fiber', 4]
  ], 'cmi:molten_etrium', 90)
  station('astronautic_mechanism', 'cmi:astronautic_mechanism', 16000, [
    ['cmi:astronautic_mechanism_basement', 1], ['cmi:nuke_cooler', 1], ['#c:wires/fluix', 1],
    ['#c:plates/titanium', 1], ['cmi:space_mechanism_part', 1]
  ], 'cmi:structural_plastic', 200)

  station('engine_frame', 'ad_astra:engine_frame', 4000, [
    ['#c:plates/stainless_steel', 4], ['#c:plates/titanium', 2], ['ad_astra:fan', 4]
  ])
  const tiers = [
    [1, 'steel', 'tungsten_steel', 'composite_tungsten_steel', 'aluminum_alloy', 'basic'],
    [2, 'desh', 'desh', 'composite_carbon_fiber', 'aluminum_alloy', 'advanced'],
    [3, 'ostrum', 'ostrum', 'superconducting_mercury', 'titanium', 'elite'],
    [4, 'calorite', 'calorite', 'composite_magnetic_conduction', 'titanium', 'ultimate']
  ]
  tiers.forEach(([i, material, hull, composite, trim, circuit]) => {
    const grade = 'tier_' + i
    const body = grade + '_rocket_body'
    const fin = grade + '_rocket_fin'
    const nose = grade + '_rocket_nose_cone'
    const plating = '#c:plates/' + hull
    const panel = '#c:plates/' + composite
    const mechanism = i <= 2 ? 'cmi:aeronautic_mechanism' : 'cmi:astronautic_mechanism'
    const tank = 'ad_astra:' + material + '_tank'
    const engine = 'ad_astra:' + material + '_engine'

    event.shaped('cmi:' + hull + '_gear', [' P ', 'P P', ' P '], {
      P: plating
    }).id(path + hull + '_gear')
    const gear = '#c:gears/' + hull

    station(nose, 'cmi:' + nose, 16000, [
      [panel, 4], [gear, 1], ['cmi:' + grade + '_aviation_cell', 1],
      ['mekanism:' + circuit + '_control_circuit', 1], ['create:flywheel', 1], [mechanism, 1]
    ], 'cmi:molten_etrium', 90)
    station(body, 'cmi:' + body, 4000, [
      [plating, 2], [panel, 1], ['#c:plates/' + trim, 1]
    ], 'cmi:silicon_rubber', 100)
    station(fin, 'cmi:' + fin, 4000, [
      [plating, 2], ['#c:plates/' + trim, 1]
    ], 'cmi:molten_etrium', 90)
    station(material + '_engine', engine, 16000, [
      [panel, 4], [gear, 2], [mechanism, 1], ['ad_astra:engine_frame', 1]
    ])
    station(material + '_tank', tank, 16000, [
      [panel, 2], [plating, 2], ['#c:plates/' + trim, 1], ['create:fluid_tank', 1]
    ])
    const slot = ['cmi:' + nose]
    for (let bodySlot = 0; bodySlot < 6; bodySlot++) slot.push('cmi:' + body)
    slot.push('cmi:' + fin, tank, tank, 'cmi:' + fin, 'cmi:' + fin, engine, 'cmi:' + fin)
    event.custom({
      type: 'ad_astra:nasa_workbench',
      ingredients: slot.map(item => ({item: item})),
      result: {id: 'ad_astra:' + grade + '_rocket', count: 1}
    }).id(path + grade + '_rocket')
  })
})
