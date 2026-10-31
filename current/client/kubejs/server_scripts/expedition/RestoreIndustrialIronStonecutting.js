// priority: -1290
// Restore Create 6.0.8's native route after CMI removals and before the
// existing SelectedParallelRecipes (-1300) retention audit. Keep CMI routes.
ServerEvents.recipes(event => {
  event.custom({
    type: 'minecraft:stonecutting',
    count: 2,
    ingredient: { tag: 'forge:ingots/iron' },
    result: 'create:industrial_iron_block'
  }).id('expedition:selected_native/create/industrial_iron_block_from_ingots_iron_stonecutting')
})
