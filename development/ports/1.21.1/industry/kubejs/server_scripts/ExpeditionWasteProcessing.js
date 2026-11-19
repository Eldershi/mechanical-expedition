ServerEvents.recipes(event => {
  const path = 'expedition:factory/waste_processing/'
  const fluid = (id, amount) => ({type: 'neoforge:single', fluid: id, amount: amount == null ? 100 : amount})
  const item = id => ({item: id})
  const result = (id, count) => ({id: id, count: count == null ? 1 : count})
  const liquid = (id, amount) => ({id: id, amount: amount == null ? 100 : amount})
  const fluorite = {tag: 'c:dusts/fluorite'}
  const poloniumElectrolyte = 'cmi:polonium_containing_electrolyte'
  const plutoniumElectrolyte = 'cmi:plutonium_containing_electrolyte'
  const poloniumFeed = 'cmi:polonium_containing_solution'
  const acid = 'cmi:radioactive_acid_solution'
  const polonium = 'cmi:polonium_solution'
  const precipitate = 'cmi:radioactive_sediment'
  const plutoniumCrystal = 'cmi:plutonium_ionized_crystal'
  const plutoniumFeed = 'cmi:plutonium_containing_solution'
  const plutoniumExtract = 'cmi:plutonium_extract_solution'
  const raw = 'cmi:raw_polonium'
  const powder = 'cmi:raw_polonium_dust'

  const kettle = (name, ingredients, results, options) => event.custom(Object.assign({
    type: 'createcraftedbeginning:reactor_kettle',
    ingredients: ingredients,
    results: results,
    processing_time: 100
  }, options || {})).id(path + name)

  kettle('refine_waste', [item('alexscaves:unrefined_waste')], [result('alexscaves:toxic_paste', 5)], {
    gas_results: [liquid('cmi:nuke_waste')]
  })
  event.custom({
    type: 'createcraftedbeginning:fractionation_tower',
    gas_ingredients: [{ingredient: {gas: 'cmi:nuke_waste'}, amount: 200}],
    ingredients: [],
    results: [],
    layer_outputs: [
      {layer: 1, fluid: liquid(poloniumElectrolyte)},
      {layer: 2, fluid: liquid(plutoniumElectrolyte)}
    ],
    temperature: 'chilled',
    processing_time: 100
  }).id(path + 'separate_waste')
  kettle('radioactive_sediment', [fluorite, fluorite, fluid(poloniumElectrolyte)],
    [result(precipitate), liquid(poloniumFeed)])
  kettle('raw_polonium', [fluorite, fluid(poloniumFeed)], [result(raw)], {temperature: 'chilled'})
  kettle('plutonium_ionized_crystal', [fluorite, fluorite, fluid(plutoniumElectrolyte)],
    [result(plutoniumCrystal)], {temperature: 'chilled'})
  kettle('plutonium_solution', [item(precipitate), item(plutoniumCrystal), fluid('cmi:nitric_acid')], [liquid(plutoniumFeed)])
  kettle('plutonium_extract', [fluid(plutoniumFeed), fluid('modernfoundry:molten_uranium', 180)],
    [result('immersiveengineering:raw_uranium'), liquid(plutoniumExtract, 200)])
  kettle('radioactive_acid', [fluid(plutoniumExtract), fluid('mekanism:hydrogen_chloride')], [liquid(acid)], {
    gas_results: [liquid('cmi:radioactive_mixture')]
  })
  kettle('sludge_extract', [item(powder), fluid(acid)], [result('cmi:sludge_extract'), liquid(polonium)])
  const zinc = {tag: 'c:dusts/zinc'}
  kettle('reduced_polonium', [zinc, zinc, zinc, zinc, zinc, fluid(polonium)],
    [result('cmi:reduced_polonium'), result('alltheores:dirty_zinc_dust', 5)])

  event.recipes.create.crushing(powder, raw).id(path + 'polonium_crushing')
  event.recipes.create.milling(powder, raw).id(path + 'polonium_milling')
  event.custom({
    type: 'kaleidoscope_cookery:millstone',
    ingredient: item(raw),
    result: result(powder)
  }).id(path + 'polonium_kaleidoscope_mill')
  event.custom({
    type: 'vintageimprovements:polishing',
    ingredients: [item(raw)],
    results: [result(powder)],
    processing_time: 20,
    speed_limits: 1
  }).id(path + 'polonium_belt_grinding')
  event.custom({
    type: 'create_enchantment_industry:grinding',
    ingredients: [item(raw)],
    results: [result(powder)]
  }).id(path + 'polonium_mechanical_grinding')
})
