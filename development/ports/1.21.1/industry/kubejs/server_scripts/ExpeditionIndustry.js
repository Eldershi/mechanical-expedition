ServerEvents.recipes(event => {
  const item = id => ({ item: id })
  const tag = id => ({ tag: id })
  const stack = id => ({ id: id, count: 1 })
  const compat = 'expedition:upstream_compat/'

  // A Create belt supplies the flexible seal for the non-Thermal recipe.
  event.custom({
    type: 'minecraft:crafting_shaped',
    pattern: ['ABA', 'CDC', ' E '],
    key: {
      A: [tag('c:ingots/cast_iron'), tag('c:plates/cast_iron')],
      B: item('vintageimprovements:redstone_module'),
      C: item('cmi:copper_mechanism'),
      D: item('create:spout'),
      E: item('create:belt_connector')
    },
    result: stack('steam_letters:advanced_spout')
  }).id(compat + 'advanced_spout_cast_iron')

  event.custom({
    type: 'minecraft:crafting_shaped',
    pattern: ['PCP', 'MGM', ' X '],
    key: {
      P: tag('c:plates/bronze'),
      C: item('steam_letters:bronze_casing'),
      M: item('cmi:bronze_mechanism'),
      G: item('create:mechanical_press'),
      X: tag('c:storage_blocks/bronze')
    },
    result: stack('steam_letters:steam_hammer')
  }).id(compat + 'steam_hammer_previous_materials')

  event.custom({
    type: 'minecraft:crafting_shapeless',
    ingredients: [item('steam_letters:steam_mechanism')],
    result: stack('cmi:bronze_mechanism')
  }).id('expedition:industry/bronze_mechanism')

  // Reuse SSW's bundled Vintage schema to form the CMI copper mechanism.
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const copper = 'cmi:incomplete_copper_mechanism'
  create.sequenced_assembly('cmi:copper_mechanism', '#c:plates/copper', [
    vintage.curving(copper, copper).itemAsHead('cmi:mechanism_mold'),
    create.filling(copper, [copper, Fluid.of('minecraft:water', 1000)]),
    create.deploying(copper, [copper, Ingredient.of('#c:glass_blocks')]),
    create.deploying(copper, [copper, 'create:belt_connector']),
    create.deploying(copper, [copper, 'cmi:mechanical_mechanism_part'])
  ]).transitionalItem(copper).loops(1).id('expedition:industry/copper_mechanism')

  // Hexa serializes its casting recipes under the modernfoundry namespace.
  const castingMaterials = [
    ['iron', 'c:molten_iron'],
    ['copper', 'c:molten_copper'],
    ['andesite', 'c:molten_andesite_alloy']
  ]
  const castTypes = ['multi_use', 'single_use']
  castingMaterials.forEach(material => {
    const metal = material[0]
    const fluid = material[1]
    const basement = `cmi:${metal}_mechanism_basement`
    castTypes.forEach(cast => {
      const id = `expedition:industry/casting/${metal}_basement_${cast}`
      event.custom({
        type: 'modernfoundry:casting_table',
        id: id,
        cast: tag(`modernfoundry:casts/${cast}/mechanism`),
        cast_consumed: cast === 'single_use',
        fluid: { amount: 90, tag: fluid },
        cooling_time: 50,
        result: item(basement)
      }).id(id)
    })
  })
})
