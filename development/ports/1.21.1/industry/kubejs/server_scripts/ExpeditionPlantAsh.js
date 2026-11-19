ServerEvents.tags('item', event => {
  event.add('cmi:tree_barks', ['farmersdelight:tree_bark', 'cmi:rubber_tree_bark'])
  event.add('expedition:ash_plants', [
    '#createaddition:plants', '#minecraft:flowers', '#minecraft:leaves',
    '#cmi:tree_barks', '#c:dusts/wood'
  ])
})

ServerEvents.recipes(event => {
  event.smelting('cmi:plant_ash', '#expedition:ash_plants')
    .id('expedition:factory/plant_ash/smelting')
  event.custom({
    type: 'immersiveengineering:fertilizer',
    growthModifier: 1.2,
    input: {tag: 'c:plant_ash'}
  }).id('expedition:factory/plant_ash/cloche_fertilizer')
})
