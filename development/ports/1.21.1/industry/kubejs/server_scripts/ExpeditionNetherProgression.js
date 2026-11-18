ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const transitional = 'cmi:incomplete_nether_mechanism'
  const path = 'expedition:factory/nether/'
  const lapis = 'mekanism:dust_lapis_lazuli'
  const part = 'cmi:magical_mechanism_part'

  create.milling(lapis, 'minecraft:lapis_lazuli').id(path + 'lapis_dust')
  event.shapeless(part, [lapis, 'minecraft:amethyst_shard', 'cmi:dreamcore_crystal'])
    .id(path + 'magical_mechanism_part')
  create.mixing(Fluid.of('modernfoundry:liquid_soul', 1000), [
    Ingredient.of(['minecraft:soul_soil', 'minecraft:soul_sand'])
  ]).superheated().processingTime(150).id(path + 'liquid_soul')
  create.sequenced_assembly('cmi:nether_mechanism', 'create:cinder_flour', [
    vintage.curving(transitional, transitional).itemAsHead('cmi:mechanism_mold'),
    create.deploying(transitional, [transitional, 'minecraft:magma_cream']),
    create.filling(transitional, [transitional, Fluid.of('modernfoundry:liquid_soul', 250)]),
    create.deploying(transitional, [transitional, 'minecraft:gold_nugget']),
    create.deploying(transitional, [transitional, part])
  ]).transitionalItem(transitional).loops(1).id(path + 'nether_mechanism')
})
