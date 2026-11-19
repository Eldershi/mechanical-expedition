ServerEvents.recipes(event => {
  const create = event.recipes.create
  const path = 'expedition:factory/syrup/'
  const syrup = amount => Fluid.of('cmi:sugar_syrup', amount)
  const cane = 'minecraft:sugar_cane'
  const fiber = 'cmi:sugarcane_fiber'
  const beetroot = Ingredient.of('#c:crops/beetroot')
  const sugar = 'minecraft:sugar'

  create.compacting([fiber, syrup(100)], [cane]).id(path + 'press_cane')
  create.compacting([fiber, syrup(150)], [cane, sugar]).id(path + 'press_cane_with_sugar')
  create.compacting(syrup(100), [beetroot]).id(path + 'press_beetroot')
  create.compacting(syrup(100), [beetroot, sugar]).id(path + 'press_beetroot_with_sugar')

  create.emptying(['6x minecraft:paper', syrup(10)], fiber).id(path + 'drain_fiber')
  event.smelting('3x minecraft:paper', fiber).cookingTime(200).id(path + 'dry_fiber')
  event.smoking('3x minecraft:paper', fiber).cookingTime(100).id(path + 'smoke_fiber')
  create.mixing(sugar, [syrup(10)]).heated().id(path + 'sugar')

  const crops = [
    ['potato', {tag: 'c:crops/potato'}, 80],
    ['melon_slice', {item: 'minecraft:melon_slice'}, 20],
    ['tomato', {tag: 'c:crops/tomato'}, 80],
    ['sweet_berries', {item: 'minecraft:sweet_berries'}, 50],
    ['apple', {item: 'minecraft:apple'}, 80],
    ['glow_berries', {item: 'minecraft:glow_berries'}, 100],
    ['beetroot', {tag: 'c:crops/beetroot'}, 40]
  ]
  for (const method of ['basin_fermenting', 'bulk_fermenting']) {
    for (const [name, crop, amount] of crops) {
      event.custom({
        type: 'createdieselgenerators:' + method,
        ingredients: [crop, {type: 'fluid_stack', fluid: 'cmi:sugar_syrup', amount: amount}],
        processing_time: 100,
        results: [{id: 'immersiveengineering:ethanol', amount: amount}]
      }).id(path + method + '/' + name)
    }
  }
})
