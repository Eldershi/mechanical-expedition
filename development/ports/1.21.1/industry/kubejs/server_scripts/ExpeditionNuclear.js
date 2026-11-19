ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/nuclear/'
  const cement = 'createdieselgenerators:white_cement'
  const cryotheum = 'neoecoae:cryotheum_solution'
  const station = (id, output, count, energy, parts, fluid, amount) => {
    event.custom({
      type: 'neoecoae:integrated_working_station',
      energy: energy,
      itemOutput: {id: output, count: count},
      inputItems: parts.map(([item, count]) => item.startsWith('#')
        ? {tag: item.substring(1), count: count} : {item: item, count: count}),
      inputFluid: {fluid: fluid, amount: amount}
    }).id(path + id)
  }

  const redstoneAcid = 'immersiveengineering:redstone_acid'
  create.filling('cmi:activated_graphite_chunk', [
    Ingredient.of(['immersiveengineering:ingot_hop_graphite', 'immersiveengineering:dust_hop_graphite']),
    Fluid.of(redstoneAcid, 100)
  ]).id(path + 'activated_graphite_chunk')

  create.compacting('2x cmi:refined_radiation_rock', ['alexscaves:radrock'])
    .superheated().id(path + 'refined_radiation_rock')
  create.filling('cmi:acid_washed_radiation_rock', [
    'cmi:refined_radiation_rock', Fluid.of('mekanism:sulfuric_acid', 100)
  ]).id(path + 'acid_washed_radiation_rock')
  const separation = path + 'separate_acid_washed_radiation_rock'
  event.custom({
    type: 'vintageimprovements:centrifugation',
    ingredients: [{ item: 'cmi:acid_washed_radiation_rock' }],
    results: [{ id: 'cmi:dense_oxide_film' }, { id: 'alexscaves:toxic_paste' }],
    processing_time: 400,
    minimal_rpm: 100
  }).id(separation)
  create.mixing(Fluid.of('cmi:radiation_resistant_creosote', 250), ['cmi:dense_oxide_film'])
    .superheated().id(path + 'radiation_resistant_creosote')
  event.custom({
    type: 'mekanism:oxidizing',
    input: { item: 'alexscaves:toxic_paste' },
    output: { id: 'cmi:radon', amount: 10 }
  }).id(path + 'radon_from_toxic_paste')
  event.custom({
    type: 'mekanism:rotary',
    fluid_input: { fluid: 'cmi:radon', amount: 1 },
    fluid_output: { id: 'cmi:radon', amount: 1 },
    chemical_input: { chemical: 'cmi:radon', amount: 1 },
    chemical_output: { id: 'cmi:radon', amount: 1 }
  }).id(path + 'condense_radon')
  create.mixing('alexscaves:polymer_plate', [
    'mekanism:hdpe_sheet',
    Fluid.of('cmi:radon', 100),
    Fluid.of('cmi:radiation_resistant_creosote', 100)
  ]).superheated().id(path + 'polymer_plate_from_acid_wash')

  create.mixing('cmi:entro_crystal', [
    'extendedae_plus:oblivion_singularity', 'cmi:dreamcore_crystal', 'create:shadow_steel'
  ]).superheated().id(path + 'entro_crystal')
  station('entro_alloy', 'cmi:entro_alloy', 2, 8000, [
    ['cmi:entro_crystal', 1], ['ad_astra:etrium_ingot', 1]
  ], cryotheum, 100)
  station('quantum_mechanism_part', 'cmi:quantum_mechanism_part', 4, 1000, [
    ['extendedae_plus:oblivion_singularity', 1], ['cmi:entro_alloy', 1], ['#c:gems/dreamcore', 1]
  ], cryotheum, 200)
  station('fissile_core', 'alexscaves:fissile_core', 1, 16000, [
    ['#c:plates/lead', 4], ['alexscaves:cinder_brick', 2], ['mekanism:yellow_cake_uranium', 4]
  ], cement, 1000)
  station('nuclear_mechanism_basement', 'cmi:nuclear_mechanism_basement', 1, 2000, [
    ['#c:plates/lead', 2], ['alexscaves:polymer_plate', 2], ['#c:plates/refined_glowstone', 1],
    ['#c:wires/fluix', 4]
  ], cement, 1000)
  station('nuclear_mechanism', 'cmi:nuclear_mechanism', 1, 16000, [
    ['cmi:nuclear_mechanism_basement', 1], ['#c:plates/composite_tungsten_steel', 1],
    ['cmi:nuke_cooler', 1], ['alexscaves:fissile_core', 1], ['cmi:quantum_mechanism_part', 1]
  ], 'cmi:silicon_rubber', 100)
  const incomplete = 'cmi:incomplete_nuclear_mechanism'
  create.sequenced_assembly('cmi:nuclear_mechanism', 'cmi:nuclear_mechanism_basement', [
    create.deploying(incomplete, [incomplete, Ingredient.of('#c:plates/composite_tungsten_steel')]),
    create.deploying(incomplete, [incomplete, 'cmi:nuke_cooler']),
    vintage.laser_cutting(incomplete, incomplete).energy(1000).maxChargeRate(1000),
    create.filling(incomplete, [incomplete, Fluid.of('cmi:silicon_rubber', 100)]),
    create.deploying(incomplete, [incomplete, 'alexscaves:fissile_core']),
    create.deploying(incomplete, [incomplete, 'cmi:quantum_mechanism_part'])
  ]).transitionalItem(incomplete).loops(1).id(path + 'sequenced_nuclear_mechanism')
})
