StartupEvents.registry('item', event => {
  const parts = {
    electric_gear: 'precision_mechanism', planetary_gear: 'precision_mechanism',
    circuit_board: 'electron_tube', polymer_ingot: 'sturdy_sheet', efficiency_module_2: 'brass_hand',
    semi_finished_steel: 'iron_sheet', aluminum_slag: 'sturdy_sheet', graphite_dust: 'powdered_obsidian',
    data_kib: 'electron_tube', data_mib: 'precision_mechanism',
    trade_credit: 'brass_nugget', coolant: 'brass_sheet'
  }
  Object.entries(parts).forEach(([part, texture]) => {
    event.create('expedition_industry:' + part).texture('create:item/' + texture)
  })
  event.create('expedition_industry:differential').texture('create:item/precision_mechanism')
  event.create('expedition_industry:incomplete_differential', 'create:sequenced_assembly')
    .texture('create:item/incomplete_precision_mechanism')
})
