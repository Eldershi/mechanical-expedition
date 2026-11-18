ServerEvents.recipes(event => {
  const path = 'expedition:factory/plating/'
  event.recipes.create.mixing(Fluid.of('cmi:plating_solution', 1000), [
    Ingredient.of('#c:dusts/chromium'),
    Fluid.of('mekanism:sulfuric_acid', 500)
  ]).id(path + 'solution')

  event.custom({
    type: 'immersiveengineering:bottling_machine',
    fluid: {fluid: 'cmi:plating_solution', amount: 1000},
    inputs: [{tag: 'c:gears/steel'}],
    results: [{id: 'cmi:chromeplated_steel_gear'}]
  }).id(path + 'gear')
})
