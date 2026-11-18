ServerEvents.tags('item', event => {
  event.add('c:gems/dreamcore', 'cmi:dreamcore_crystal')
  event.add('c:plates/silicon', 'ae2:printed_silicon')
  event.add('cmi:peat_gen', ['cmi:peat_block', 'cmi:peat'])
})

ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements

  event.shaped('cmi:wooden_gear', [' P ', 'PSP', ' P '], {
    P: '#minecraft:planks', S: 'minecraft:stick'
  }).id('expedition:factory/wooden_gear')
  create.pressing('cmi:andesite_alloy_plate', 'create:andesite_alloy')
    .id('expedition:factory/andesite_alloy_plate')
  create.cutting('2x cmi:incomplete_large_cogwheel', [
    Ingredient.of('#c:gears/wooden')
  ]).id('expedition:factory/unfinished_large_cogwheel')
  create.crushing([
    'cmi:dreamcore_crystal', CreateItem.of('cmi:dreamcore_crystal', 0.1)
  ], ['cmi:dreamcore_ore']).id('expedition:factory/dreamcore_crystal')
  event.shapeless('4x cmi:mechanical_mechanism_part', [
    '#c:gears/wooden', '#c:plates/andesite_alloy', '#c:gems/dreamcore'
  ]).id('expedition:factory/mechanical_mechanism_part')

  ;['mechanism', 'plate'].forEach(form => {
    const id = `cmi:${form}_mold`
    event.custom({
      type: 'immersiveengineering:blueprint',
      category: 'molds',
      inputs: [{ basePredicate: { tag: 'c:plates/iron' }, count: 4 }],
      result: { id: id }
    }).id(`cmi:blueprint/${form}_mold`)
  })

  vintage.curving('ae2:printed_silicon', 'ae2:silicon').itemAsHead('cmi:plate_mold')
    .id('expedition:factory/silicon_plate')
})
