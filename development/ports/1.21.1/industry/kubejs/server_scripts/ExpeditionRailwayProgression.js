ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/railway/'
  const mechanism = 'cmi:railway_mechanism'
  const blank = 'create:unprocessed_obsidian_sheet'
  const chassis = 'cmi:incomplete_railway_mechanism'

  create.cutting('2x cmi:incomplete_cogwheel', ['cmi:wooden_gear'])
    .id(path + 'unfinished_cogwheel')
  create.mixing(Fluid.of('cmi:molten_industrial_iron', 90), [
    Ingredient.of('#c:dusts/iron')
  ]).superheated().id(path + 'molten_industrial_iron')
  create.sequenced_assembly('cmi:dense_sturdy_sheet', Ingredient.of('#c:plates/obsidian'), [
    create.filling(blank, [blank, Fluid.of('modernfoundry:molten_obsidian', 250)]),
    create.deploying(blank, [blank, 'create:sturdy_sheet']),
    create.pressing(blank, blank)
  ]).transitionalItem(blank).loops(1).id(path + 'dense_sturdy_sheet')
  create.sequenced_assembly(mechanism, Ingredient.of('#c:plates/dense_obsidian'), [
    vintage.curving(chassis, chassis).itemAsHead('cmi:mechanism_mold'),
    create.filling(chassis, [chassis, Fluid.of('cmi:molten_industrial_iron', 90)]),
    create.deploying(chassis, [chassis, Ingredient.of('#create:incomplete_cogwheels')]),
    create.deploying(chassis, [chassis, Ingredient.of('#c:plates/brass')]),
    create.deploying(chassis, [chassis, 'cmi:mechanical_mechanism_part'])
  ]).transitionalItem(chassis).loops(1).id(path + 'railway_mechanism')

  const devices = [
    ['create:track_station', 'minecraft:compass', 2],
    ['create:track_observer', 'minecraft:comparator', 2],
    ['create:track_signal', 'create:transmitter', 2],
    ['create:controls', 'create_connected:control_chip', 1],
    ['railways:track_coupler', 'create:minecart_coupling', 2]
  ]
  devices.forEach(device => {
    const output = device[0]
    const control = device[1]
    const amount = device[2]
    event.shaped(Item.of(output, amount), ['A', 'C', 'M'], {
      A: control, C: 'create:railway_casing', M: mechanism
    }).id(path + output.split(':')[1])
  })
})
