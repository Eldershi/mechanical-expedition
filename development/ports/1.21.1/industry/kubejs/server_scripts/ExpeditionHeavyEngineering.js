ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/heavy_engineering/'
  const mechanism = 'cmi:heavy_engineering_mechanism'
  const augment = 'cmi:heavy_engineering_mechanism_augment'
  const transitional = 'cmi:incomplete_heavy_engineering_mechanism'
  const steel = Ingredient.of('#c:plates/steel')

  event.custom({
    type: 'immersiveengineering:refinery',
    catalyst: { tag: 'c:plates/copper' },
    energy: 120,
    input0: { fluid: 'immersiveengineering:plantoil', amount: 100 },
    input1: { fluid: 'cmi:naphtha', amount: 100 },
    result: { id: 'cmi:lubricating_oil', amount: 200 }
  }).id(path + 'lubricating_oil')

  create.mechanical_crafting(`4x ${augment}`, ['GSE'], {
    G: Ingredient.of('#c:gears/electrum'),
    S: 'immersiveengineering:component_steel',
    E: 'immersiveengineering:electron_tube'
  }).id(path + 'augment')

  create.sequenced_assembly(mechanism, steel, [
    vintage.curving(transitional, transitional).itemAsHead('cmi:mechanism_mold'),
    create.deploying(transitional, [transitional, augment]),
    create.filling(transitional, [transitional, Fluid.of('cmi:lubricating_oil', 100)]),
    vintage.vacuumizing(transitional, transitional),
    create.deploying(transitional, [transitional, Ingredient.of('#c:rods/invar')]),
    create.deploying(transitional, [transitional, 'cmi:engineering_mechanism_part'])
  ]).transitionalItem(transitional).loops(1).id(path + 'heavy_engineering_mechanism')

  event.shaped('createdieselgenerators:huge_diesel_engine', ['ABA', 'CDC', 'AEA'], {
    A: steel,
    B: 'minecraft:flint_and_steel',
    C: mechanism,
    D: 'create:steam_engine',
    E: 'create:fluid_pipe'
  }).id(path + 'huge_diesel_engine')
})
