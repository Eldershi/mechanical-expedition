// priority: -1290
// Compact iron nuggets in a basin while keeping the remaining coin recipes.
ServerEvents.recipes(event => {
  event.remove({ id: 'createdeco:pressing/coins/iron_coin' })
  event.custom({
    type: 'create:compacting',
    ingredients: [
      { item: 'minecraft:iron_nugget' }, { item: 'minecraft:iron_nugget' },
      { item: 'minecraft:iron_nugget' }, { item: 'minecraft:iron_nugget' },
      { item: 'minecraft:iron_nugget' }, { item: 'minecraft:iron_nugget' },
      { item: 'minecraft:iron_nugget' }, { item: 'minecraft:iron_nugget' },
      { item: 'minecraft:iron_nugget' }
    ],
    results: [{ item: 'minecraft:iron_ingot' }]
  }).id('expedition:compacting/iron_ingot_from_nuggets')
})

ServerEvents.afterRecipes(event => {
  const report = {
    recipe: event.countRecipes({ id: 'expedition:compacting/iron_ingot_from_nuggets' }),
    coinPressing: event.countRecipes({ id: 'createdeco:pressing/coins/iron_coin' }),
    ingredients: 0, ironNuggets: 0, output: '', outputCount: 0, outputChance: 0, heat: ''
  }
  event.forEachRecipe({ id: 'expedition:compacting/iron_ingot_from_nuggets' }, recipe => {
    const inputs = recipe.getIngredients()
    report.ingredients = inputs.size()
    for (let i = 0; i < inputs.size(); i++) {
      if (inputs.get(i).test(Item.of('minecraft:iron_nugget'))) report.ironNuggets++
    }
    const results = recipe.getRollableResults()
    if (results.size() === 1) {
      const result = results.get(0)
      const stack = result.getStack()
      report.output = String(stack.id)
      report.outputCount = stack.getCount()
      report.outputChance = result.getChance()
    }
    report.heat = String(recipe.getRequiredHeat())
  })
  report.passed = report.recipe === 1 && report.coinPressing === 0 &&
    report.ingredients === 9 && report.ironNuggets === 9 &&
    report.output === 'minecraft:iron_ingot' && report.outputCount === 1 &&
    report.outputChance === 1 && report.heat === 'NONE'
  console.info('[Iron Nugget Compacting] ' + JSON.stringify(report))
  if (!report.passed) throw new Error('Iron nugget compacting recipe audit failed')
})
