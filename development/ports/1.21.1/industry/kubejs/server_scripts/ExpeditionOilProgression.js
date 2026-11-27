ServerEvents.recipes(event => {
  const path = 'expedition:factory/oil/'
  const create = event.recipes.create
  const diesel = 'createdieselgenerators:'
  const fluid = (id, amount) => Fluid.of(id, amount)
  const cmi = (name, amount) => fluid(`cmi:${name}`, amount)
  const distill = (name, input, amount, products) => {
    event.custom({
      type: diesel + 'distillation',
      ingredients: [{ type: 'fluid_tag', fluid_tag: input, amount: amount }],
      heat_requirement: 'heated',
      processing_time: 120,
      results: products.map(product => ({ id: product[0], amount: product[1] }))
    }).id(path + name)
  }

  // A separate feed lets the tower select the pack's fractions while pure
  // crude still uses the Diesel Generators diesel and gasoline recipes.
  create.mixing(cmi('conditioned_crude_oil', 1000), [
    fluid(diesel + 'crude_oil', 1000), fluid('minecraft:water', 100)
  ]).heated().id(path + 'conditioned_crude_oil')
  distill('crude_fractions', 'cmi:conditioned_crude_oil', 2000, [
    ['cmi:bitumen', 500], ['cmi:sulfric_diesel', 500], ['cmi:kerosene', 500]
  ])
  distill('kerosene_fraction', 'cmi:kerosene', 100, [
    [diesel + 'gasoline', 50], ['cmi:naphtha', 50]
  ])
  create.mixing([fluid(diesel + 'diesel', 80), 'mekanism:dust_sulfur'], [
    cmi('sulfric_diesel', 100)
  ]).heated().id(path + 'diesel_desulfurization')

  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: { tag: 'c:plates/vanadium' },
    energy: 120,
    input0: { fluid: diesel + 'gasoline', amount: 200 },
    input1: { tag: 'c:steam', amount: 100 },
    result: { id: 'cmi:cracked_gasoline', amount: 200 }
  }).id(path + 'cracked_gasoline')
  const mixedFractions = (name, input, amount, layers) => {
    event.custom({
      type: 'createcraftedbeginning:fractionation_tower',
      ingredients: [{type: 'neoforge:tag', tag: input, amount: amount}],
      layer_outputs: layers,
      results: [],
      processing_time: 120,
      temperature: 'heated'
    }).id(path + name)
  }
  mixedFractions('cracked_gasoline_fractions', 'cmi:cracked_gasoline', 500, [
    {layer: 1, fluid: {id: 'cmi:naphtha', amount: 100}},
    {layer: 2, fluid: {id: 'cmi:benzene', amount: 100}},
    {layer: 3, gas: {id: 'cmi:light_olefin', amount: 200}}
  ])
  mixedFractions('creosote_fractions', 'c:creosote', 100, [
    {layer: 1, fluid: {id: 'cmi:phenol', amount: 50}},
    {layer: 2, gas: {id: 'cmi:light_olefin', amount: 50}}
  ])

  create.milling([
    CreateItem.of('vintageimprovements:vanadium_nugget', 0.10),
    CreateItem.of('minecraft:iron_nugget', 0.40),
    CreateItem.of('create:crushed_raw_iron', 0.40)
  ], 'create:crimsite').id(path + 'vanadium_from_crimsite')
})
