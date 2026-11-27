ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/continuity/'

  for (const [output, input] of [
    ['wood_chip_briquette', Ingredient.of('#c:dusts/wood')],
    ['compressed_wood_chip_briquette', 'cmi:wood_chip_briquette'],
    ['densely_packed_wood_chip_briquette', 'cmi:compressed_wood_chip_briquette']
  ]) create.compacting('cmi:' + output, [input, input, input, input]).id(path + output)
  create.compacting('cmi:creosote_wood_chip_briquette', [
    'cmi:densely_packed_wood_chip_briquette', Fluid.of('immersiveengineering:creosote', 250)
  ]).id(path + 'creosote_wood_chip_briquette')

  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: {tag: 'c:plates/iron'},
    energy: 120,
    input0: {fluid: 'cmi:benzene', amount: 100},
    input1: {fluid: 'mekanism:ethene', amount: 100},
    result: {id: 'cmi:phenol', amount: 200}
  }).id(path + 'phenol_refining')

  const magic = 'cmi:magical_mechanism_part'
  const assembly = (id, input, steps) => {
    const part = 'cmi:incomplete_' + id + '_mechanism'
    create.sequenced_assembly('cmi:' + id + '_mechanism', input, steps(part))
      .transitionalItem(part).loops(1).id(path + id)
  }
  event.custom({
    type: 'ae2:charger',
    ingredient: {item: 'minecraft:amethyst_shard'},
    result: {id: 'cmi:charged_amethyst'}
  }).id(path + 'charged_amethyst')
  create.mechanical_crafting('4x cmi:ender_mechanism_basement', ['PED'], {
    P: 'vintageimprovements:enderium_sheet',
    E: 'minecraft:ender_pearl',
    D: 'minecraft:slime_ball'
  }).id(path + 'ender_basement')
  assembly('ender', 'cmi:ender_mechanism_basement', part => [
    create.deploying(part, [part, 'minecraft:ender_pearl']),
    create.filling(part, [part, Fluid.sizedIngredientOf('#c:molten_enderium', 90)]),
    create.deploying(part, [part, 'ars_nouveau:source_gem']),
    vintage.laser_cutting(part, part).energy(1000).maxChargeRate(1000),
    create.deploying(part, [part, magic])
  ])

  create.mechanical_crafting('2x cmi:glowstone_lumen_tube', ['CAB', 'A A', 'BAC'], {
    A: 'vintageimprovements:lumium_wire', B: 'vintageimprovements:cobalt_rod', C: 'vintageimprovements:cobalt_sheet'
  }).id(path + 'lumen_tube')
  create.mechanical_crafting('4x cmi:flux_mechanism_part', ['CAC', ' R '], {
    C: 'immersiveengineering:wirecoil_copper', A: 'ae2:calculation_processor', R: 'minecraft:redstone'
  }).id(path + 'flux_part')
  create.mechanical_crafting('cmi:resonant_tube', ['QEQ'], {
    Q: 'cmi:pure_quartz_prism', E: 'immersiveengineering:electron_tube'
  }).id(path + 'resonant_tube')
  assembly('photosensitive', 'cmi:pure_quartz_prism', part => [
    create.deploying(part, [part, 'cmi:resonant_tube']),
    vintage.laser_cutting(part, part).energy(1000).maxChargeRate(1000),
    create.deploying(part, [part, 'minecraft:amethyst_shard']),
    create.pressing(part, part),
    create.deploying(part, [part, 'cmi:flux_mechanism_part'])
  ])
})
