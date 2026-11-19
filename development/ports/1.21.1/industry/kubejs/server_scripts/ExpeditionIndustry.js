ServerEvents.recipes(event => {
  const item = id => ({ item: id })
  const tag = id => ({ tag: id })
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

  const bronze = 'cmi:incomplete_bronze_mechanism'
  create.sequenced_assembly('cmi:bronze_mechanism', '#c:plates/bronze', [
    vintage.curving(bronze, bronze).itemAsHead('cmi:mechanism_mold'),
    create.filling(bronze, [bronze, Fluid.of('modernfoundry:molten_bronze', 90)]),
    create.deploying(bronze, [bronze, 'steampowered:bronze_cogwheel']),
    create.deploying(bronze, [bronze, Ingredient.of('#c:plates/bronze')]),
    create.deploying(bronze, [bronze, 'cmi:mechanical_mechanism_part'])
  ]).transitionalItem(bronze).loops(1).id('expedition:industry/bronze_mechanism')

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
