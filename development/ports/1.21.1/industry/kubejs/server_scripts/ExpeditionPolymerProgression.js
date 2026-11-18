ServerEvents.recipes(event => {
  const path = 'expedition:factory/polymer/'
  const refine = (name, catalyst, energy, inputs, output) => {
    const recipe = {
      type: 'immersiveengineering:refinery',
      catalyst: { tag: `c:plates/${catalyst}` },
      energy: energy,
      input0: { fluid: inputs[0][0], amount: inputs[0][1] },
      result: { id: `cmi:${name}`, amount: output }
    }
    if (inputs.length === 2) recipe.input1 = { fluid: inputs[1][0], amount: inputs[1][1] }
    event.custom(recipe).id(path + name)
  }

  refine('cracked_diesel', 'vanadium', 120, [
    ['createdieselgenerators:diesel', 100], ['steam_letters:steam', 100]
  ], 200)
  event.custom({
    type: 'createdieselgenerators:distillation',
    ingredients: [{ type: 'fluid_tag', fluid_tag: 'cmi:cracked_diesel', amount: 1000 }],
    heat_requirement: 'heated',
    processing_time: 120,
    results: [
      { id: 'cmi:light_aldehyde', amount: 750 },
      { id: 'cmi:acetylene', amount: 250 }
    ]
  }).id(path + 'cracked_diesel_fractions')
  refine('vinyl_alcohol', 'silver', 120, [['cmi:acetylene', 100]], 100)
  refine('polyvinyl_alcohol', 'copper', 6400, [['cmi:vinyl_alcohol', 2000]], 2000)
  refine('structural_plastic', 'copper', 120, [
    ['cmi:light_aldehyde', 100], ['cmi:polyvinyl_alcohol', 100]
  ], 200)

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
