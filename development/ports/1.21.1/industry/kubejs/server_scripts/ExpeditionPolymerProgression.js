ServerEvents.recipes(event => {
  const path = 'expedition:factory/polymer/'
  const refine = (name, catalyst, energy, input0, output, input1) => {
    const recipe = {
      type: 'immersiveengineering:refinery',
      catalyst: { tag: `c:plates/${catalyst}` },
      energy: energy,
      input0: input0,
      result: { id: `cmi:${name}`, amount: output }
    }
    if (input1) recipe.input1 = input1
    event.custom(recipe).id(path + name)
  }

  refine('cracked_diesel', 'vanadium', 120, { fluid: 'createdieselgenerators:diesel', amount: 100 }, 200,
    { tag: 'c:steam', amount: 100 })
  event.custom({
    type: 'createcraftedbeginning:fractionation_tower',
    ingredients: [{type: 'neoforge:single', fluid: 'cmi:cracked_diesel', amount: 1000}],
    layer_outputs: [
      {layer: 1, fluid: {id: 'cmi:light_aldehyde', amount: 750}},
      {layer: 2, gas: {id: 'cmi:acetylene', amount: 250}}
    ],
    results: [],
    processing_time: 120,
    temperature: 'heated'
  }).id(path + 'cracked_diesel_fractions')
  refine('vinyl_alcohol', 'silver', 120, { fluid: 'cmi:acetylene', amount: 100 }, 100)
  refine('polyvinyl_alcohol', 'copper', 6400, { fluid: 'cmi:vinyl_alcohol', amount: 2000 }, 2000)
  refine('structural_plastic', 'copper', 120, { fluid: 'cmi:light_aldehyde', amount: 100 }, 200,
    { fluid: 'cmi:polyvinyl_alcohol', amount: 100 })

  event.custom({
    type: 'immersiveengineering:bottling_machine',
    fluid: { fluid: 'cmi:structural_plastic', amount: 200 },
    inputs: [{ item: 'ae2:quartz_glass' }],
    results: [{ id: 'mekanism:structural_glass' }]
  }).id(path + 'structural_glass')

  event.recipes.create.mixing('2x cmi:osmium_tile', [
    Ingredient.of('#c:plates/aluminum'),
    Ingredient.of('#c:plates/osmium'),
    Fluid.of('cmi:structural_plastic', 200)
  ]).id(path + 'osmium_tile')
})
