// priority: -200
// Full client and server restart required. Run after the pack's food modifications.
// Copy existing properties explicitly: the callback overload resets food values.
// Only remove the full-hunger limit.
// Consumption, hunger, saturation, effects, containers and eat time remain native.
const ExpeditionAlwaysEatFoodBuilder = Java.loadClass('dev.latvian.mods.kubejs.item.FoodBuilder')
ItemEvents.modification(event => {
  let changed = 0
  ForgeRegistries.ITEMS.getEntries().forEach(entry => {
    let item = entry.getValue()
    let food = item.getFoodProperties()
    if (food !== null && !food.canAlwaysEat()) {
      event.modify(item, modify => modify.setFoodProperties(new ExpeditionAlwaysEatFoodBuilder(food).alwaysEdible().build()))
      changed++
    }
  })
  console.info('[Expedition Always Eat] Enabled full-hunger eating for ' + changed + ' foods')
})
