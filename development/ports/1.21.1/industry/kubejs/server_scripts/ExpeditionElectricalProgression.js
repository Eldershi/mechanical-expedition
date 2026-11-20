ServerEvents.tags('item', event => {
  event.add('c:plates/industrial_iron', 'createdeco:industrial_iron_sheet')
})

ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/electrical/'
  const precision = 'create:incomplete_precision_mechanism'
  const rotor = 'cmi:incomplete_motor_rotor'
  const coil = 'cmi:incomplete_coil_mechanism'

  create.sequenced_assembly('create:precision_mechanism', Ingredient.of('#c:plates/brass'), [
    vintage.curving(precision, precision).itemAsHead('cmi:mechanism_mold'),
    create.filling(precision, [precision, Fluid.sizedIngredientOf('#c:molten_brass', 90)]),
    create.deploying(precision, [precision, 'create:electron_tube']),
    create.deploying(precision, [precision, Ingredient.of('#create:incomplete_cogwheels')]),
    create.deploying(precision, [precision, 'cmi:mechanical_mechanism_part'])
  ]).transitionalItem(precision).loops(1).id(path + 'precision_mechanism')

  create.sequenced_assembly('cmi:motor_rotor', Ingredient.of('#c:rods/iron'), [
    create.cutting(rotor, rotor),
    create.deploying(rotor, [rotor, Ingredient.of('#c:plates/industrial_iron')]),
    create.deploying(rotor, [rotor, Ingredient.of('#c:wires/copper')])
  ]).transitionalItem(rotor).loops(1).id(path + 'motor_rotor')

  const redstone = ['minecraft:redstone', 'minecraft:redstone', 'minecraft:redstone', 'minecraft:redstone']
  create.mixing(Fluid.of('modernfoundry:molten_signalum', 360), [
    Fluid.sizedIngredientOf('#c:molten_copper', 270), Fluid.sizedIngredientOf('#c:molten_lead', 90)
  ].concat(redstone)).heated().id(path + 'molten_signalum')
  create.mixing('4x cmi:engineering_mechanism_part', [
    Ingredient.of('#c:plates/constantan'), 'immersiveengineering:electron_tube',
    'cmi:dreamcore_crystal', Fluid.sizedIngredientOf('#c:molten_signalum', 90)
  ]).id(path + 'engineering_mechanism_part')

  event.custom({
    type: 'immersiveengineering:mixer',
    energy: 1600,
    fluid: { tag: 'c:molten_lead', amount: 90 },
    inputs: [{ tag: 'c:dusts/redstone' }],
    result: { id: 'immersiveengineering:redstone_acid', amount: 200 }
  }).id(path + 'redstone_acid')

  create.sequenced_assembly('cmi:coil_mechanism', Ingredient.of('#c:plates/iron'), [
    vintage.curving(coil, coil).itemAsHead('cmi:mechanism_mold'),
    create.deploying(coil, [coil, 'cmi:motor_rotor']),
    create.filling(coil, [coil, Fluid.of('immersiveengineering:redstone_acid', 200)]),
    vintage.vacuumizing(coil, coil),
    create.deploying(coil, [coil, Ingredient.of('#c:plates/electrum')]),
    create.deploying(coil, [coil, 'cmi:engineering_mechanism_part'])
  ]).transitionalItem(coil).loops(1).id(path + 'coil_mechanism')

  event.shapeless('2x createaddition:portable_energy_interface', [
    'create:brass_casing', 'cmi:coil_mechanism', '#c:plates/industrial_iron'
  ]).id(path + 'portable_energy_interface')
  create.mechanical_crafting('createaddition:tesla_coil', ['PAP', ' I ', 'BMB', 'VCV'], {
    P: '#c:plates/copper', A: 'immersiveengineering:coil_lv', I: '#c:ingots/andesite_alloy',
    B: '#c:plates/brass', M: 'cmi:coil_mechanism', V: '#c:plates/vanadium', C: 'create:brass_casing'
  }).id(path + 'tesla_coil')
})
