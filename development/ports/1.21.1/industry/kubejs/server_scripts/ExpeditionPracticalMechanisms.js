ServerEvents.recipes(event => {
  const create = event.recipes.create
  const vintage = event.recipes.vintageimprovements
  const path = 'expedition:factory/mechanisms/'
  const magic = 'cmi:magical_mechanism_part'
  const mechanical = 'cmi:mechanical_mechanism_part'
  const engineering = 'cmi:engineering_mechanism_part'
  const andesite = 'cmi:incomplete_andesite_mechanism'
  const light = 'cmi:incomplete_light_engineering_mechanism'
  const mold = 'cmi:mechanism_mold'
  const augment = 'cmi:light_engineering_mechanism_augment'

  event.shapeless(magic, ['#c:dusts/lapis', '#c:gems/amethyst', '#c:gems/dreamcore'])
    .id(path + 'magical_part')

  event.shapeless('cmi:andesite_mechanism', [
    'cmi:andesite_mechanism_basement', '#c:plates/andesite_alloy',
    'create:cogwheel', 'create:large_cogwheel', mechanical, '#c:tools/wrench'
  ]).keepIngredient('#c:tools/wrench').id(path + 'andesite_manual')

  create.sequenced_assembly('cmi:andesite_mechanism', Ingredient.of('#c:plates/andesite'), [
    vintage.curving(andesite, andesite).itemAsHead(mold),
    create.filling(andesite, [andesite, Fluid.of('cmi:molten_andesite_alloy', 90)]),
    create.deploying(andesite, [andesite, Ingredient.of('#create:incomplete_cogwheels')]),
    create.deploying(andesite, [andesite, Ingredient.of('#create:incomplete_large_cogwheels')]),
    create.deploying(andesite, [andesite, mechanical])
  ]).transitionalItem(andesite).loops(1).id(path + 'andesite')

  create.mechanical_crafting('4x cmi:laser_diode', ['WPQ'], {
    W: Ingredient.of('#c:wires/electrum'),
    P: Ingredient.of('#c:plates/invar'),
    Q: Ingredient.of('#c:prisms/pure_quartz')
  }).id(path + 'laser_diode')
  create.mechanical_crafting('2x immersiveengineering:component_electronic', ['DT', 'QW'], {
    D: 'cmi:laser_diode', T: Ingredient.of('#immersiveengineering:treated_wood_slab'),
    Q: Ingredient.of('#c:gems/quartz'), W: Ingredient.of('#c:wires/electrum')
  }).id(path + 'electronic_component')
  create.mechanical_crafting(`4x ${augment}`, ['GID'], {
    G: Ingredient.of('#c:gears/copper'),
    I: 'immersiveengineering:component_iron', D: 'cmi:laser_diode'
  }).id(path + 'light_augment')
  create.sequenced_assembly('cmi:light_engineering_mechanism', Ingredient.of('#c:plates/industrial_iron'), [
    vintage.curving(light, light).itemAsHead(mold),
    create.deploying(light, [light, augment]),
    create.filling(light, [light, Fluid.of('immersiveengineering:creosote', 100)]),
    vintage.vacuumizing(light, light),
    create.deploying(light, [light, Ingredient.of('#c:rods/constantan')]),
    create.deploying(light, [light, engineering])
  ]).transitionalItem(light).loops(1).id(path + 'light_engineering')
})
