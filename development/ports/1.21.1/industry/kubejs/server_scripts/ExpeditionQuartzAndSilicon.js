ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/quartz/'
  create.milling('mekanism:dust_quartz', 'minecraft:quartz').id(path + 'quartz_dust')
  vintage.pressurizing([
    'cmi:pure_quartz_dust', 'immersiveengineering:slag'
  ], ['mekanism:dust_quartz', 'cmi:lime_dust']).heated().id(path + 'pure_quartz_dust')

  event.custom({
    type: 'immersiveengineering:mixer',
    fluid: { tag: 'minecraft:water', amount: 500 },
    inputs: [
      { item: 'minecraft:amethyst_shard' },
      { basePredicate: { tag: 'c:seeds' }, count: 32 }
    ],
    result: { id: 'cmi:crystal_catalyt', amount: 1000 },
    energy: 1600
  }).id(path + 'crystal_catalyst')
  create.compacting('cmi:pure_quartz_prism', [
    'cmi:pure_quartz_dust', Fluid.of('cmi:crystal_catalyt', 200)
  ]).id(path + 'pure_quartz_prism')

  ;['seared_stone', 'scorched_stone'].forEach(stone => {
    create.mixing('cmi:silicon_mixture', [
      'immersiveengineering:dust_coke', 'cmi:pure_quartz_dust',
      Fluid.of(`modernfoundry:${stone}`, 250)
    ]).superheated().id(path + 'silicon_mixture_' + stone)
  })
  event.custom({
    type: 'immersiveengineering:blast_furnace',
    input: { item: 'cmi:silicon_mixture' },
    result: { id: 'ae2:silicon' },
    slag: { id: 'immersiveengineering:slag' },
    time: 600
  }).id(path + 'silicon')
})
