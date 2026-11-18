ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/metallurgy/'
  const oreCoke = 'immersiveengineering:dust_coke'
  const moltenIron = Fluid.of('modernfoundry:molten_iron', 90)
  const moltenCastIron = Fluid.of('cmi:molten_cast_iron', 90)
  const lime = 'cmi:lime_dust'
  const bloom = 'cmi:refined_iron_bloom'
  const slag = 'immersiveengineering:slag'

  create.crushing(lime, 'create:limestone').id(path + 'lime')
  event.custom({
    type: 'immersiveengineering:blast_furnace',
    input: { item: 'create:limestone' },
    result: { id: 'cmi:furnaced_lime', count: 4 },
    time: 30
  }).id(path + 'furnaced_lime')

  vintage.pressurizing(moltenCastIron, [moltenIron, oreCoke])
    .heated().id(path + 'molten_cast_iron')
  ;['multi_use', 'single_use'].forEach(cast => {
    const id = path + 'cast_iron_' + cast
    event.custom({
      type: 'modernfoundry:casting_table',
      id: id,
      cast: { tag: `modernfoundry:casts/${cast}/ingot` },
      cast_consumed: cast === 'single_use',
      fluid: { amount: 90, tag: 'c:molten_cast_iron' },
      cooling_time: 50,
      result: { item: 'cmi:cast_iron_ingot' }
    }).id(id)
  })
  event.custom({
    type: 'immersiveengineering:crusher',
    input: { tag: 'c:ingots/cast_iron' },
    result: { id: 'cmi:cast_iron_dust' },
    energy: 2400
  }).id(path + 'cast_iron_dust')
  create.pressing('cmi:cast_iron_plate', Ingredient.of('#c:ingots/cast_iron'))
    .id(path + 'cast_iron_plate')

  const castIron = Ingredient.of(['#c:ingots/cast_iron', '#c:dusts/cast_iron'])
  create.mixing(bloom, [castIron, lime]).superheated().processingTime(300)
    .id(path + 'refined_iron_bloom_mixing')
  event.custom({
    type: 'immersiveengineering:arc_furnace',
    input: { tag: 'c:dusts/cast_iron' },
    additives: [{ tag: 'c:dusts/lime' }],
    results: [{ id: 'immersiveengineering:ingot_steel' }],
    slag: { id: slag },
    time: 400,
    energy: 8000
  }).id(path + 'steel_arc_furnace')
  vintage.pressurizing(Fluid.of('modernfoundry:molten_steel', 90), [bloom])
    .superheated().processingTime(200).id(path + 'molten_steel')

  create.mixing(Fluid.of('cmi:chromium_solution', 200), [
    Fluid.of('mekanism:sulfuric_acid', 200), 'alltheores:ruby_dust'
  ]).id(path + 'chromium_solution')
  create.compacting('cmi:chromium_dust', [Fluid.of('cmi:chromium_solution', 200)])
    .heated().id(path + 'chromium_dust')
  event.smelting('cmi:chromium_ingot', '#c:dusts/chromium').id(path + 'chromium_ingot')
  event.custom({
    type: 'immersiveengineering:arc_furnace',
    input: { tag: 'c:ingots/steel' },
    additives: [{ tag: 'c:ingots/chromium' }, { tag: 'c:ingots/constantan' }],
    results: [{ id: 'cmi:stainless_steel_ingot' }],
    slag: { id: slag },
    time: 100,
    energy: 8000
  }).id(path + 'stainless_steel')
})
