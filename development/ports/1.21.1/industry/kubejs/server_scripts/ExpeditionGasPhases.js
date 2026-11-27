ServerEvents.recipes(event => {
  const path = 'expedition:factory/gas/'
  const phase = (name, gas, fluid, cooling, alternate, batchSize) => {
    const batch = batchSize || 100
    const input = id => ({type: 'neoforge:single', fluid: id, amount: batch})
    event.custom({
      type: 'createcraftedbeginning:reactor_kettle',
      ingredients: [input(fluid)],
      gas_results: [{id: gas, amount: batch}],
      results: [],
      temperature: 'heated',
      processing_time: batch
    }).id(path + 'vaporize/' + name)
    if (alternate) {
      event.custom({
        type: 'createcraftedbeginning:reactor_kettle',
        ingredients: [input(alternate)],
        gas_results: [{id: gas, amount: batch}],
        results: [],
        temperature: 'heated',
        processing_time: batch
      }).id(path + 'vaporize/' + name + '_from_' + alternate.split(':')[0])
    }
    if (cooling) {
      event.custom({
        type: 'createcraftedbeginning:reactor_kettle',
        ingredients: [],
        gas_ingredients: [{ingredient: {gas: gas}, amount: batch}],
        results: [{id: fluid, amount: batch}],
        temperature: cooling,
        processing_time: batch
      }).id(path + 'condense/' + name)
    }
  }

  // Phase recipes use the pack's transfer ratio. The gas network still calculates pressure.
  phase('acetylene', 'cmi:acetylene', 'cmi:acetylene', null, null, 1)
  phase('light_olefin', 'cmi:light_olefin', 'cmi:light_olefin', null, null, 1)
  phase('radon', 'cmi:radon', 'cmi:radon', 'superchilled')
  phase('nitrogen', 'expedition:nitrogen', 'cmi:liquid_nitrogen', 'superchilled')
  phase('oxygen', 'expedition:oxygen', 'mekanism:oxygen', 'superchilled', 'ad_astra:oxygen')
  phase('hydrogen', 'expedition:hydrogen', 'mekanism:hydrogen', 'superchilled', 'ad_astra:hydrogen')
  phase('steam', 'createcraftedbeginning:steam', 'mekanism:steam', null, 'steampowered:steam')
  phase('ethene', 'expedition:ethene', 'mekanism:ethene', 'superchilled')
  phase('chlorine', 'expedition:chlorine', 'mekanism:chlorine', 'superchilled')
  phase('hydrogen_chloride', 'expedition:hydrogen_chloride', 'mekanism:hydrogen_chloride', 'superchilled')
  phase('sulfur_dioxide', 'expedition:sulfur_dioxide', 'mekanism:sulfur_dioxide', 'superchilled', 'vintageimprovements:sulfur_dioxide')
  phase('sulfur_trioxide', 'expedition:sulfur_trioxide', 'mekanism:sulfur_trioxide', 'chilled', 'vintageimprovements:sulfur_trioxide')
  phase('deuterium', 'expedition:deuterium', 'mekanismgenerators:deuterium', 'superchilled')
  phase('tritium', 'expedition:tritium', 'mekanismgenerators:tritium', 'superchilled')
  phase('fusion_fuel', 'expedition:fusion_fuel', 'mekanismgenerators:fusion_fuel', 'superchilled')
})
