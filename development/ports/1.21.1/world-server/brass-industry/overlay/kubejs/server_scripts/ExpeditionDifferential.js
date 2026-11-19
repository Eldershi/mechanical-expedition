ServerEvents.recipes(event => {
  const part = 'expedition_industry:incomplete_differential'
  const create = event.recipes.create
  create.sequenced_assembly('2x expedition_industry:differential', Ingredient.of('#c:plates/brass'), [
    create.deploying(part, [part, 'create:large_cogwheel']),
    create.deploying(part, [part, 'create:large_cogwheel']),
    create.deploying(part, [part, 'create:precision_mechanism'])
  ]).transitionalItem(part).loops(1).id('expedition_industry:differential')
})
