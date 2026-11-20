ServerEvents.recipes(event => {
  const path = 'expedition:factory/mineral_chemistry/'
  const create = event.recipes.create
  const germanium = 'cmi:germanium_solution'
  const germaniumGas = 'cmi:germanium_precursor'
  const entroGas = 'cmi:entro_peroxide'
  const chaos = 'cmi:chaotic_void'
  const rotary = (id, liquid, chemical) => event.custom({
    type: 'mekanism:rotary',
    fluid_input: {fluid: liquid, amount: 100},
    chemical_output: {id: chemical, amount: 100}
  }).id(path + id)
  const crush = (id, input, output) => event.custom({
    type: 'mekanism:crushing',
    input: {item: input},
    output: {id: output}
  }).id(path + id)
  const infuse = (id, input, chemical, output) => event.custom({
    type: 'mekanism:metallurgic_infusing',
    item_input: input,
    chemical_input: {chemical: chemical, amount: 10},
    output: {id: output}
  }).id(path + id)
  const convert = (id, item, chemical) => event.custom({
    type: 'mekanism:chemical_conversion',
    input: {item: item},
    output: {id: chemical, amount: 10}
  }).id(path + id)
  const kettle = (id, spec) => event.custom(Object.assign({type: 'createcraftedbeginning:reactor_kettle'}, spec))
    .id(path + id)
  const sizedFluid = (fluid, amount) => ({type: 'neoforge:single', fluid: fluid, amount: amount})

  const sourceCrystals = [
    ['alpha', 'cmi:source_ruby', 'alltheores:ruby'],
    ['beta', 'cmi:source_sapphire', 'alltheores:sapphire'],
    ['gamma', 'cmi:source_emeraid', 'minecraft:emerald']
  ]
  kettle('blackstone_sources', {
    ingredients: [{item: 'minecraft:blackstone'}, sizedFluid('createcraftedbeginning:brimstone', 50)],
    results: sourceCrystals.map(entry => ({id: `cmi:${entry[0]}_blackstone_source`})),
    processing_time: 100
  })
  sourceCrystals.forEach(entry => {
    const [type, crystal, gem] = entry
    create.filling(crystal, [`cmi:${type}_blackstone_source`, Fluid.of('cmi:crystal_catalyt', 100)])
      .id(path + 'grow_' + type + '_source_crystal')
    event.custom({
      type: 'create_enchantment_industry:grinding',
      ingredients: [{item: crystal}],
      results: [{id: gem}]
    }).id(path + 'grind_' + type + '_source_crystal')
  })

  create.crushing('6x cmi:end_stone_dust', 'minecraft:end_stone').id(path + 'end_stone_dust_manual_only')
  create.mixing(Fluid.of('cmi:delta_unstable_solution', 200), [
    'cmi:delta_blackstone_source', 'cmi:end_stone_dust', Fluid.of('immersiveengineering:redstone_acid', 50)
  ]).heated().id(path + 'delta_unstable_solution')

  kettle('brominated_flame_retardants', {
    ingredients: [{item: 'cmi:refractory_material_powder'}, {item: 'cmi:refractory_material_powder'},
      sizedFluid('cmi:bromine', 200)],
    results: [{id: 'cmi:brominated_flame_retardants'}],
    processing_time: 100
  })
  create.compacting('2x cmi:flame_retardant_plastic', [
    'alexscaves:polymer_plate', 'cmi:brominated_flame_retardants'
  ]).superheated().id(path + 'flame_retardant_plastic')
  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: {item: 'cmi:ethylene_polymerization_catalytic_plate'},
    energy: 120,
    input0: {tag: 'c:ethene', amount: 10},
    result: {id: 'cmi:hdpe', amount: 1}
  }).id(path + 'polymerize_ethene')
  create.compacting('mekanism:hdpe_pellet', [Fluid.of('cmi:hdpe', 1000)])
    .heated().id(path + 'solidify_hdpe')

  event.custom({
    type: 'mekanism:compressing',
    item_input: {item: 'cmi:void_dust'},
    chemical_input: {chemical: 'mekanism:osmium', amount: 1},
    output: {id: 'cmi:chaotic_void_dust'}
  }).id(path + 'chaotic_void_dust')
  convert('chaotic_void', 'cmi:chaotic_void_dust', chaos)
  convert('etrium_chemical', 'cmi:etrium_dust', 'cmi:etrium')
  infuse('entro_crystal', {item: 'ae2:charged_certus_quartz_crystal'}, 'cmi:etrium', 'cmi:entro_crystal')
  infuse('spiritcore_ore', {item: 'cmi:entro_crystal'}, chaos, 'cmi:spiritcore_ore')
  infuse('infused_osmium', {tag: 'c:dusts/osmium'}, chaos, 'cmi:infuse_osmium')
  convert('infused_osmium_chemical', 'cmi:infuse_osmium', 'cmi:infuse_osmium')
  infuse('carbon_nanotube_from_osmium', {item: 'cmi:incomplete_carbon_nanotube'}, 'cmi:infuse_osmium', 'cmi:carbon_nanotube')
  infuse('piezoelectric_ceramic', {item: 'cmi:magnetic_alloy'}, 'cmi:titanium_oxide', 'cmi:piezoelectric_ceramic')

  event.custom({
    type: 'createaddition:charging',
    ingredients: [{item: 'create:chromatic_compound'}],
    results: [{id: 'cmi:overcharged_alloy_ingot'}],
    energy: 5000,
    max_charge_rate: 500
  }).id(path + 'overcharged_alloy_ingot')
  event.shapeless('ae2:pattern_encoding_terminal', [
    'cmi:overcharged_alloy_ingot', 'ae2:crafting_terminal'
  ]).id(path + 'overcharged_pattern_encoding_terminal')

  event.custom({
    type: 'ae2:inscriber',
    ingredients: {
      top: {item: 'cmi:composite_magnetic_conduction_plate'},
      middle: {item: 'cmi:ferrit_core'},
      bottom: {item: 'cmi:piezoelectric_ceramic'}
    },
    result: {id: 'cmi:magnetic_contact'},
    mode: 'press'
  }).id(path + 'magnetic_contact')
  event.custom({
    type: 'neoecoae:integrated_working_station',
    energy: 2000,
    inputItems: [
      {tag: 'c:plates/platinum', count: 8},
      {item: 'immersiveengineering:wirecoil_steel', count: 1},
      {item: 'cmi:magnetic_contact', count: 2},
      {item: 'neoecoae:energized_fluix_crystal', count: 2},
      {item: 'cmi:computing_mechanism', count: 1}
    ],
    inputFluid: {fluid: 'cmi:ferrouslime', amount: 500},
    itemOutput: {id: 'me_beam_former:wireless_energy_tower', count: 1}
  }).id(path + 'wireless_energy_tower')
  event.shaped('4x mekanismgenerators:fusion_reactor_frame', ['P#P', '#X#', 'P#P'], {
    P: 'cmi:piezoelectric_ceramic',
    '#': '#c:pellets/polonium',
    X: 'mekanism:steel_casing'
  }).id(path + 'piezoelectric_fusion_reactor_frame')

  crush('galena_dust', 'alexscaves:galena', 'cmi:galena_dust')
  create.crushing('cmi:galena_dust', 'alexscaves:galena').id(path + 'galena_dust_crushing')
  create.milling('cmi:galena_dust', 'alexscaves:galena').id(path + 'galena_dust_milling')
  const neodymiumColors = ['azure', 'scarlet']
  neodymiumColors.forEach(color => {
    const metal = `${color}_neodymium`
    const id = path + 'melt_' + metal
    event.custom({
      type: 'modernfoundry:melting',
      id: id,
      ingredient: {item: `alexscaves:${metal}_ingot`},
      result: {fluid: `cmi:molten_${metal}`, amount: 90},
      temperature: 1024,
      time: 100
    }).id(id)
  })
  event.custom({
    type: 'mekanism:enriching',
    input: {item: 'cmi:germanium_mixture'},
    output: {id: 'cmi:enriched_germanium_iron_mixture'}
  }).id(path + 'enriched_germanium_iron_mixture')
  crush('dragonite_dust', 'cmi:dragonite', 'cmi:dragonite_dust')
  create.mixing(Fluid.of(germanium, 100), [
    'cmi:dragonite_dust', Fluid.sizedIngredientOf('#c:sulfuric_acid', 100)
  ]).heated().id(path + 'dissolve_dragonite')
  rotary('germanium_precursor', germanium, germaniumGas)
  event.custom({
    type: 'mekanism:crystallizing',
    input: {chemical: germaniumGas, amount: 100},
    output: {id: 'cmi:germanium_crystal'}
  }).id(path + 'germanium_crystal')

  crush('entro_peroxide_dust', 'cmi:entro_peroxide_crystal', 'cmi:entro_peroxide_dust')
  kettle('entro_peroxide_solution', {
    ingredients: [{item: 'cmi:entro_peroxide_dust'}, sizedFluid('cmi:crystal_etching_solution', 100)],
    results: [{id: 'cmi:entro_peroxide_solution', amount: 100}],
    processing_time: 40
  })
  kettle('sodium_reducing_agent', {
    ingredients: [
      {item: 'cmi:electrolized_redstone'}, {item: 'cmi:electrolized_redstone'},
      sizedFluid('cmi:ionized_entro_solution', 100), sizedFluid('mekanism:sodium', 100)
    ],
    results: [{id: 'cmi:sodium_reducing_agent', count: 4}],
    processing_time: 40
  })
  kettle('reduce_entro_in_kettle', {
    ingredients: [{item: 'cmi:sodium_reducing_agent'}, sizedFluid('cmi:entro_peroxide_solution', 100)],
    results: [{id: 'cmi:reduced_entro_crystal'}],
    temperature: 'chilled'
  })
  rotary('entro_peroxide', 'cmi:entro_peroxide_solution', entroGas)
  event.custom({
    type: 'mekanism:reaction',
    item_input: {item: 'cmi:sodium_reducing_agent', count: 1},
    fluid_input: {fluid: 'cmi:liquid_nitrogen', amount: 50},
    chemical_input: {chemical: entroGas, amount: 100},
    item_output: {id: 'cmi:reduced_entro_crystal'},
    duration: 100
  }).id(path + 'reduce_entro_with_liquid_nitrogen')
  crush('reduced_entro_dust', 'cmi:reduced_entro_crystal', 'cmi:reduced_entro_dust')
  create.crushing('cmi:reduced_entro_dust', 'cmi:reduced_entro_crystal').id(path + 'reduced_entro_dust_crushing')
  create.milling('cmi:reduced_entro_dust', 'cmi:reduced_entro_crystal').id(path + 'reduced_entro_dust_milling')
  crush('venus_stone_dust', 'ad_astra:venus_stone', 'cmi:venus_stone_dust')

  kettle('liquid_crystal_etrium', {
    ingredients: [{item: 'cmi:etrium_mixture'}, sizedFluid('cmi:pure_crystal_source', 50)],
    results: [{id: 'cmi:liquid_crystal_etrium', amount: 100}],
    processing_time: 40
  })
  kettle('entro_compound', {
    ingredients: [sizedFluid('cmi:molten_silicon_containing_compound', 50),
      sizedFluid('cmi:delta_unstable_solution', 50), sizedFluid('cmi:pure_crystal_source', 50)],
    results: [{id: 'cmi:entro_compound', count: 4}],
    temperature: 'heated',
    processing_time: 40
  })
  kettle('entro_alloy', {
    ingredients: [sizedFluid('cmi:liquid_crystal_entro', 50), sizedFluid('cmi:crystal_entro_solution', 50)],
    results: [{id: 'cmi:entro_alloy', count: 2}],
    processing_time: 40
  })
})
