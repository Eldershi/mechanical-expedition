if (Platform.isLoaded('createcraftedbeginning')) {
  ServerEvents.recipes(event => {
    const path = 'expedition:factory/pneumatic_sealing/'
    const station = (id, energy, fluid, amount, parts) => {
      event.custom({
        type: 'neoecoae:integrated_working_station',
        energy: energy,
        itemOutput: {id: 'cmi:' + id, count: 1},
        inputFluid: {fluid: fluid, amount: amount},
        inputItems: parts.map(([item, count]) => ({item: item, count: count}))
      }).id(path + id)
    }
    station('air_tight_mechanism_basement', 2000, 'modernfoundry:molten_glass', 1000, [
      ['alltheores:osmium_plate', 2], ['cmi:chromeplated_steel_gear', 1],
      ['vintageimprovements:golden_spring', 1], ['createcraftedbeginning:airtight_sheet', 1]
    ])
    station('incomplete_air_tight_mechanism', 16000, 'cmi:silicon_rubber', 100, [
      ['cmi:air_tight_mechanism_basement', 1], ['createcraftedbeginning:gas_canister', 1],
      ['createcraftedbeginning:airtight_sheet', 1], ['ae2:quartz_glass', 1], ['cmi:engineering_mechanism_part', 1]
    ])
    event.custom({
      type: 'createcraftedbeginning:gas_injection',
      gas_ingredients: [{
        amount: 1000,
        ingredient: {gas: 'createcraftedbeginning:natural_air'},
        minimum_pressure: 125000
      }],
      ingredients: [{item: 'cmi:incomplete_air_tight_mechanism'}],
      results: [{id: 'cmi:air_tight_mechanism'}]
    }).id(path + 'air_tight_mechanism')
  })
}
