ServerEvents.recipes(event => {
  const create = event.recipes.create
  const path = 'expedition:factory/seawater/'
  const fluid = (name, amount) => Fluid.of(`cmi:${name}`, amount)
  const evaporate = (id, input, output) => {
    event.custom({
      type: 'mekanism:evaporating',
      input: { fluid: `cmi:${input}`, amount: 10 },
      output: { id: output, amount: 1 }
    }).id(path + id)
  }

  create.mixing(fluid('sea_water', 1000), [
    'mekanism:salt', Fluid.of('minecraft:water', 1000)
  ]).id(path + 'seawater_feed')
  evaporate('concentrated_sea_water', 'sea_water', 'cmi:concentrated_sea_water')
  evaporate('brine', 'concentrated_sea_water', 'cmi:brine')
  event.custom({
    type: 'immersiveengineering:mixer',
    fluid: { fluid: 'cmi:brine', amount: 500 },
    inputs: [{ basePredicate: { item: 'cmi:furnaced_lime' }, count: 4 }],
    result: { id: 'cmi:alkaline_brine', amount: 500 },
    energy: 1600
  }).id(path + 'alkaline_brine')
  create.mixing([
    fluid('lithium_containing_electrolyte', 100), 'mekanism:salt'
  ], [fluid('waste_brine', 200)]).processingTime(200).id(path + 'lithium_electrolyte')
  create.mixing([
    fluid('caustic_soda_solution', 200), 'mekanism:salt'
  ], [fluid('sea_water', 1000)]).processingTime(200).id(path + 'caustic_soda')
  evaporate('liquid_lithium', 'lithium_containing_electrolyte', 'mekanism:lithium')
})
