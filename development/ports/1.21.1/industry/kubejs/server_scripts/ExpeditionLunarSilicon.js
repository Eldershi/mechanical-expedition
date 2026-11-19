ServerEvents.recipes(event => {
  const create = event.recipes.create
  const path = 'expedition:factory/space/'
  const machalite = 'cmi:machalite'
  const powder = 'cmi:machalite_dust'
  const residue = 'cmi:pyrolyzed_moon_rock_residue'
  const molten = 'cmi:molten_pure_silicon'
  const crystal = 'cmi:single_crystal_silicon'
  const kettle = (id, recipe) => {
    event.custom(Object.assign({type: 'createcraftedbeginning:reactor_kettle'}, recipe)).id(path + id)
  }
  const hotAir = amount => [{amount: amount, ingredient: {gas: 'createcraftedbeginning:ultrawarm_air'}}]

  create.crushing(powder, machalite).id(path + 'machalite_dust_crushing')
  create.milling(powder, machalite).id(path + 'machalite_dust_milling')
  create.cutting('cmi:silicon_wafer', crystal).id(path + 'silicon_wafer_from_crystal')
  create.splashing([
    CreateItem.of(machalite, 0.60),
    CreateItem.of(powder, 0.30),
    CreateItem.of('mekanism:dirty_dust_uranium', 0.10)
  ], residue).id(path + 'wash_moon_rock_residue')

  kettle('pyrolyze_moon_rock', {
    ingredients: [{item: 'ad_astra:moon_stone'}],
    gas_ingredients: hotAir(1000),
    results: [{id: residue}],
    gas_results: [{id: 'cmi:helium_3', amount: 10}],
    temperature: 'superheated',
    processing_time: 100
  })
  kettle('molten_pure_silicon', {
    ingredients: [
      {item: powder}, {item: powder}, {item: powder}, {item: powder},
      {type: 'neoforge:single', fluid: 'cmi:polysilicone_ether', amount: 500}
    ],
    gas_ingredients: hotAir(5000),
    results: [{id: molten, amount: 1000}],
    temperature: 'heated',
    processing_time: 100
  })
  event.custom({
    type: 'modernfoundry:casting_table',
    id: path + 'cast_single_crystal_silicon',
    cast: {item: 'modernfoundry:gem_cast'},
    fluid: {fluid: molten, amount: 250},
    cooling_time: 100,
    result: {item: crystal}
  }).id(path + 'cast_single_crystal_silicon')
})
