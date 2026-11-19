ServerEvents.tags('item', event => {
  event.add('c:gems/dreamcore', 'cmi:dreamcore_crystal')
  event.add('c:plates/silicon', 'ae2:printed_silicon')
})

ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements

  event.shaped('cmi:wooden_gear', [' P ', 'PSP', ' P '], {
    P: '#minecraft:planks', S: 'minecraft:stick'
  }).id('expedition:factory/wooden_gear')
  create.pressing('cmi:andesite_alloy_plate', 'create:andesite_alloy')
    .id('expedition:factory/andesite_alloy_plate')

  event.shaped('cmi:hammer_head', ['PPP', 'III', 'PPP'], {
    P: Ingredient.of(['#c:plates/iron', '#c:plates/andesite_alloy']),
    I: Ingredient.of(['#c:ingots/iron', '#c:ingots/andesite_alloy'])
  }).id('expedition:factory/hammer_head')
  const frameworks = [
    ['andesite', '#c:plates/andesite_alloy'],
    ['brass', '#c:plates/brass'],
    ['copper', '#c:plates/copper']
  ]
  frameworks.forEach(([metal, plate]) => {
    const framework = `cmi:${metal}_casing_framework`
    event.stonecutting('4x ' + framework, plate)
      .id(`expedition:factory/${metal}_casing_framework`)
    if (metal === 'brass' || metal === 'copper') {
      create.cutting('4x ' + framework, Ingredient.of(plate)).processingTime(100)
        .id(`expedition:factory/${metal}_casing_framework_sawing`)
    }
    create.deploying(`create:${metal}_casing`, [Ingredient.of('#minecraft:planks'), framework])
      .id(`expedition:factory/${metal}_casing_from_framework`)
  })
  create.deploying('create_connected:empty_fan_catalyst', ['minecraft:iron_bars', 'cmi:brass_casing_framework'])
    .id('expedition:factory/empty_fan_catalyst_from_framework')

  create.cutting('2x cmi:incomplete_large_cogwheel', [
    Ingredient.of('#c:gears/wooden')
  ]).id('expedition:factory/unfinished_large_cogwheel')
  create.crushing([
    'cmi:dreamcore_crystal', CreateItem.of('cmi:dreamcore_crystal', 0.1)
  ], ['cmi:dreamcore_ore']).id('expedition:factory/dreamcore_crystal')
  event.shapeless('4x cmi:mechanical_mechanism_part', [
    '#c:gears/wooden', '#c:plates/andesite_alloy', '#c:gems/dreamcore'
  ]).id('expedition:factory/mechanical_mechanism_part')
  event.shapeless('4x cmi:basic_mechanism_part', ['cmi:stone_plate', '#c:gems/dreamcore'])
    .id('expedition:factory/basic_mechanism_part')

  ;['single_use', 'multi_use'].forEach(cast => {
    const recipeId = 'expedition:factory/stone_plate_' + cast
    event.custom({
      type: 'modernfoundry:casting_table',
      id: recipeId,
      cast: { tag: 'modernfoundry:casts/' + cast + '/plate' },
      cast_consumed: cast === 'single_use',
      fluid: { tag: 'minecraft:lava', amount: 100 },
      cooling_time: 40,
      result: { item: 'cmi:stone_plate' }
    }).id(recipeId)
  })

  const iron = 'cmi:incomplete_iron_mechanism'
  create.sequenced_assembly('cmi:iron_mechanism', '#c:plates/iron', [
    create.deploying(iron, [iron, Ingredient.of('#c:nuggets/iron')]),
    create.cutting(iron, iron).processingTime(100),
    create.deploying(iron, [iron, 'vintageimprovements:iron_spring']),
    create.deploying(iron, [iron, 'createaddition:iron_wire']),
    create.deploying(iron, [iron, 'cmi:basic_mechanism_part'])
  ]).transitionalItem(iron).loops(1).id('expedition:factory/mechanisms/iron')

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
