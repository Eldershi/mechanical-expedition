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
    type: 'createdieselgenerators:distillation',
    ingredients: [{type: 'fluid_stack', fluid: 'immersiveengineering:creosote', amount: 100}],
    heat_requirement: 'heated',
    processing_time: 120,
    results: [{id: 'cmi:phenol', amount: 50}, {id: 'cmi:light_olefin', amount: 50}]
  }).id(path + 'phenol')
  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: {tag: 'c:plates/iron'},
    energy: 120,
    input0: {fluid: 'cmi:benzene', amount: 100},
    input1: {fluid: 'mekanism:ethene', amount: 100},
    result: {id: 'cmi:phenol', amount: 200}
  }).id(path + 'phenol_refining')

  const magic = 'cmi:magical_mechanism_part'
  const mold = 'cmi:mechanism_mold'
  const applications = (part, ingredients) => ingredients.map(ingredient => create.deploying(part, [part, ingredient]))
  const assembly = (id, input, steps) => {
    const part = 'cmi:incomplete_' + id + '_mechanism'
    create.sequenced_assembly('cmi:' + id + '_mechanism', input, steps(part))
      .transitionalItem(part).loops(1).id(path + id)
  }
  assembly('pig_iron', 'vintageimprovements:pig_iron_sheet', part => [
    vintage.curving(part, part).itemAsHead(mold),
    create.cutting(part, part),
    create.filling(part, [part, Fluid.of('modernfoundry:molten_pig_iron', 45)])
  ].concat(applications(part, ['vintageimprovements:pig_iron_rod', magic])))
  assembly('colorful', Ingredient.of('#minecraft:planks'), part => [
    vintage.curving(part, part).itemAsHead(mold)
  ].concat(applications(part, ['minecraft:red_dye', 'minecraft:green_dye', 'minecraft:blue_dye', magic])))
  assembly('enchanted', 'minecraft:lapis_lazuli', part => [
    vintage.curving(part, part).itemAsHead(mold),
    create.deploying(part, [part, 'create:experience_nugget']),
    create.filling(part, [part, Fluid.of('create_enchantment_industry:experience', 50)]),
    create.pressing(part, part),
    create.deploying(part, [part, magic])
  ])
  event.custom({
    type: 'ae2:charger',
    ingredient: {item: 'minecraft:amethyst_shard'},
    result: {id: 'cmi:charged_amethyst'}
  }).id(path + 'charged_amethyst')
  assembly('sculk', 'minecraft:sculk_catalyst', part => [
    vintage.curving(part, part).itemAsHead(mold)
  ].concat(applications(part, ['minecraft:echo_shard', 'cmi:charged_amethyst']), [
    create.pressing(part, part), create.deploying(part, [part, magic])
  ]))
  create.mechanical_crafting('4x cmi:ender_mechanism_basement', ['PED'], {
    P: 'vintageimprovements:enderium_sheet',
    E: 'minecraft:ender_pearl',
    D: 'minecraft:slime_ball'
  }).id(path + 'ender_basement')
  assembly('ender', 'cmi:ender_mechanism_basement', part => [
    create.deploying(part, [part, 'minecraft:ender_pearl']),
    create.filling(part, [part, Fluid.of('modernfoundry:molten_enderium', 90)]),
    create.deploying(part, [part, 'ars_nouveau:source_gem']),
    vintage.laser_cutting(part, part).energy(1000).maxChargeRate(1000),
    create.deploying(part, [part, magic])
  ])

  create.mechanical_crafting('2x cmi:glowstone_lumen_tube', ['CAB', 'A A', 'BAC'], {
    A: 'vintageimprovements:lumium_wire', B: 'vintageimprovements:cobalt_rod', C: 'vintageimprovements:cobalt_sheet'
  }).id(path + 'lumen_tube')
  create.mechanical_crafting('4x cmi:reinforced_mechanism_augment', ['ST', 'IL'], {
    S: 'vintageimprovements:signalum_sheet', T: 'cmi:glowstone_lumen_tube',
    I: 'cmi:inscribed_silicon', L: 'vintageimprovements:lumium_sheet'
  }).id(path + 'reinforced_augment')
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
  assembly('reinforced', Ingredient.of('#c:plates/electrum'), part => [
    create.deploying(part, [part, 'cmi:reinforced_mechanism_augment']),
    vintage.laser_cutting(part, part).energy(1000).maxChargeRate(1000),
    create.deploying(part, [part, 'vintageimprovements:nickel_rod']),
    create.deploying(part, [part, 'vintageimprovements:signalum_wire']),
    create.pressing(part, part),
    create.deploying(part, [part, 'cmi:flux_mechanism_part'])
  ])
})
