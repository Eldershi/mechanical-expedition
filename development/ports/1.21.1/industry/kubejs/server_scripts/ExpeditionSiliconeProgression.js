ServerEvents.tags('item', event => {
  event.add('cmi:vinegar_rice', 'farmersdelight:rice')
  if (Platform.isLoaded('kaleidoscope_cookery')) {
    event.add('cmi:vinegar_rice', '#c:seeds/rice')
  }
})

ServerEvents.recipes(event => {
  const path = 'expedition:factory/silicone/'
  const rice = { tag: 'cmi:vinegar_rice' }
  event.custom({
    type: 'createdieselgenerators:basin_fermenting',
    ingredients: [rice, { type: 'fluid_stack', fluid: 'minecraft:water', amount: 200 }],
    processing_time: 200,
    results: [{ id: 'cmi:vinegar', amount: 200 }]
  }).id(path + 'vinegar')
  event.custom({
    type: 'createdieselgenerators:distillation',
    ingredients: [{ type: 'fluid_tag', fluid_tag: 'cmi:vinegar', amount: 200 }],
    heat_requirement: 'heated',
    processing_time: 120,
    results: [{ id: 'cmi:vinegar_acid', amount: 100 }, { id: 'minecraft:water', amount: 100 }]
  }).id(path + 'vinegar_acid')

  event.recipes.create.mixing(Fluid.of('cmi:light_silicone_ether', 200), [
    Ingredient.of('#c:silicon'),
    Fluid.of('cmi:light_olefin', 100)
  ]).heated().id(path + 'light_silicone_ether')
  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: { tag: 'c:plates/copper' },
    energy: 6400,
    input0: { fluid: 'cmi:light_silicone_ether', amount: 2000 },
    result: { id: 'cmi:polysilicone_ether', amount: 2000 }
  }).id(path + 'polysilicone_ether')
  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: { tag: 'c:plates/copper' },
    energy: 6400,
    input0: { fluid: 'cmi:polysilicone_ether', amount: 2000 },
    input1: { fluid: 'cmi:vinegar_acid', amount: 100 },
    result: { id: 'cmi:silicon_rubber', amount: 4000 }
  }).id(path + 'silicon_rubber_fluid')

  const castRubber = (name, plate) => {
    const id = path + name
    const recipe = {
      type: 'modernfoundry:casting_table',
      id: id,
      fluid: { tag: 'cmi:silicon_rubber', amount: 200 },
      result: { item: `cmi:${name}` },
      cooling_time: 20
    }
    if (plate) recipe.cast = { tag: 'modernfoundry:casts/multi_use/plate' }
    event.custom(recipe).id(id)
  }
  castRubber('silicon_rubber', false)
  castRubber('silicon_rubber_plate', true)
})
