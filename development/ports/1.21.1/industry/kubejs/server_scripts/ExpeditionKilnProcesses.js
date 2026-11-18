ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/kiln/'

  vintage.pressurizing('cmi:red_mud', [
    Ingredient.of(['#mekanism:dirty_dusts/aluminum', '#c:raw_materials/aluminum']),
    Ingredient.of('#c:dusts/fluorite')
  ]).id(path + 'red_mud')
  event.custom({
    type: 'immersiveengineering:bottling_machine',
    fluid: { fluid: 'immersiveengineering:redstone_acid', amount: 100 },
    inputs: [{ item: 'cmi:red_mud' }],
    results: [{ id: 'immersiveengineering:dust_aluminum' }]
  }).id(path + 'aluminum_dust')

  create.mixing('cmi:kaolinite', ['minecraft:clay', 'minecraft:calcite'])
    .id(path + 'kaolinite')
  event.shaped('cmi:kaolinite', ['KK', 'KK'], { K: 'cmi:kaolinite_ball' })
    .id(path + 'kaolinite_from_balls')
  event.custom({
    type: 'immersiveengineering:arc_furnace',
    input: { item: 'cmi:kaolinite' },
    additives: [
      { basePredicate: { tag: 'c:dusts/hop_graphite' }, count: 4 },
      { basePredicate: { item: 'minecraft:gravel' }, count: 4 }
    ],
    results: [{ id: 'cmi:refractory_grout', count: 8 }],
    time: 100,
    energy: 50000
  }).id(path + 'refractory_grout')
  event.smelting('immersiveindustry:refractory_kiln_brick', 'cmi:refractory_grout')
    .id(path + 'refractory_kiln_brick')

  event.custom({
    type: 'immersiveengineering:arc_furnace',
    input: { tag: 'c:ingots/osmium' },
    additives: [],
    results: [{ id: 'cmi:pure_semi_molten_osmium' }],
    time: 100,
    energy: 1000
  }).id(path + 'semi_molten_osmium')
  const saltpeter = Ingredient.of('#c:dusts/saltpeter')
  create.mixing([
    Fluid.of('cmi:nitric_acid', 200), 'immersiveengineering:slag'
  ], [saltpeter, saltpeter, saltpeter, saltpeter])
    .superheated().processingTime(200).id(path + 'nitric_acid')
  event.custom({
    type: 'immersiveengineering:coke_oven',
    input: { item: 'minecraft:charcoal' },
    result: { id: 'immersiveengineering:coal_coke' },
    creosote: 1000,
    time: 900
  }).id(path + 'charcoal_coke')
})
