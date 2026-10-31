// priority: -1100
// Restore Create 6.0.8's native heated copper + zinc -> 2 brass ingots.
// Separate ID keeps CMI's molten-metal mixing and alloying routes available.
const ExpeditionBrassMixingId = 'expedition:mixing/brass_ingot'
ServerEvents.recipes(event => {
  event.custom({
    type: 'create:mixing',
    heatRequirement: 'heated',
    ingredients: [{ tag: 'forge:ingots/copper' }, { tag: 'forge:ingots/zinc' }],
    results: [{ count: 2, item: 'create:brass_ingot' }]
  }).id(ExpeditionBrassMixingId)
})

// Inspect the recipes after native deserialization, on startup and /reload.
ServerEvents.afterRecipes(event => {
  const report = {
    id: ExpeditionBrassMixingId,
    count: event.countRecipes({ id: ExpeditionBrassMixingId }),
    originalMixingRetained: event.countRecipes({ id: 'create:mixing/brass_ingot' }) === 1,
    originalAlloyingRetained: event.countRecipes({ id: 'tconstruct:smeltery/alloys/molten_brass' }) === 1,
    ingredientsMatch: false,
    output: '',
    outputCount: 0,
    heat: ''
  }
  event.forEachRecipe({ id: ExpeditionBrassMixingId }, recipe => {
    const inputs = recipe.getIngredients()
    report.ingredientsMatch = inputs.size() === 2 &&
      inputs.get(0).test(Item.of('minecraft:copper_ingot')) &&
      inputs.get(1).test(Item.of('create:zinc_ingot')) &&
      !inputs.get(0).test(Item.of('minecraft:iron_ingot')) &&
      !inputs.get(1).test(Item.of('minecraft:iron_ingot'))
    const output = recipe.getRollableResults().get(0).getStack()
    report.output = String(output.id)
    report.outputCount = output.getCount()
    report.heat = String(recipe.getRequiredHeat())
  })
  report.passed = report.count === 1 && report.ingredientsMatch &&
    report.output === 'create:brass_ingot' && report.outputCount === 2 &&
    report.heat === 'HEATED' && report.originalMixingRetained && report.originalAlloyingRetained
  JsonIO.write('kubejs/exported/brass-mixing-restored.json', report)
  if (!report.passed) throw new Error('Restored brass mixing recipe verification failed: ' + JSON.stringify(report))
  console.info('[Expedition] Native brass mixing restored: copper + zinc -> 2 brass; heated; auditPassed=' + report.passed)
})
