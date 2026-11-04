// priority: -1290
// Remove the iron-nugget coin pressing recipe; the existing square crafting
// recipe can be packed by Create's mechanical press and basin.
const IronPackingPress = Java.loadClass('com.simibubi.create.content.kinetics.press.MechanicalPressBlockEntity')
const IronPackingTypes = Java.loadClass('com.simibubi.create.AllRecipeTypes')

ServerEvents.recipes(event => {
  event.remove({ id: 'createdeco:pressing/coins/iron_coin' })
})

ServerEvents.afterRecipes(event => {
  let report = {coinPressing: event.countRecipes({id: 'createdeco:pressing/coins/iron_coin'}), candidates: []}
  try {
    event.forEachRecipe({type: 'minecraft:crafting_shaped', output: 'minecraft:iron_ingot'}, recipe => {
      const inputs = recipe.getIngredients()
      if (inputs.size() !== 9) return
      let ironNuggets = 0
      for (let i = 0; i < inputs.size(); i++) {
        if (inputs.get(i).test(Item.of('minecraft:iron_nugget'))) ironNuggets++
      }
      if (ironNuggets !== 9) return
      report.candidates.push({
        id: String(recipe.getId()),
        ingredients: inputs.size(),
        ironNuggets: ironNuggets,
        canCompress: IronPackingPress.canCompress(recipe),
        ignoredByAutomation: IronPackingTypes.shouldIgnoreInAutomation(recipe)
      })
    })
    report.passed = report.coinPressing === 0 && report.candidates.some(row => row.canCompress && !row.ignoredByAutomation)
  } catch (error) {
    report.passed = false
    report.error = String(error)
  }
  console.info('[Iron Nugget Packing] ' + JSON.stringify(report))
})
