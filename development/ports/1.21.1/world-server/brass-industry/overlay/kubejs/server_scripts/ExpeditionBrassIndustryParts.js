ServerEvents.tags('item', event => {
  event.add('c:storage_blocks/industrial_iron', 'create:industrial_iron_block')
  event.add('c:ingots/industrial_iron', 'createdeco:industrial_iron_ingot')
})
ServerEvents.recipes(event => {
  const industry = 'expedition_industry:'
  const space = 'expedition_space:'
  const part = (name, count, ingredients) => event.shapeless(Item.of(industry + name, count), ingredients)
    .id(industry + 'part/' + name)
  part('electric_gear', 2, ['create:large_cogwheel', 'create:electron_tube', '#c:wires/copper'])
  part('planetary_gear', 2, ['create:cogwheel', 'create:large_cogwheel', 'create:andesite_alloy'])
  part('circuit_board', 2, ['create:electron_tube', 'mekanism:basic_control_circuit'])
  part('polymer_ingot', 2, ['mekanism:hdpe_pellet', '#c:plates/tin'])
  part('efficiency_module_2', 1, [space + 'efficiency_module', space + 'lime_circuit_board', 'mekanism:elite_control_circuit'])
  part('coolant', 2, ['minecraft:ice', 'minecraft:snowball', 'mekanism:salt'])
  event.shapeless('expedition_space:tin_hard_disk', ['expedition_industry:data_kib', '#c:ingots/tin', 'create:cogwheel'])
    .id(industry + 'part/tin_disk')
  event.shapeless('expedition_space:brass_hard_disk', ['expedition_industry:data_mib', 'create:brass_sheet', 'create:cogwheel'])
    .id(industry + 'part/brass_disk')
  const decor = (name, ingredient) => event.stonecutting(Item.of('design_decor:' + name, 4), ingredient)
    .id(industry + 'construction/' + name)
  ;['green_container', 'red_container', 'industrial_gear', 'industrial_gear_large',
    'ochrum_crushing_wheel', 'crushing_wheel_controller'].forEach(name => decor(name, 'create:industrial_iron_block'))
  ;['industrial_gold_block', 'gold_boiler', 'gold_boiler_structure', 'gold_boiler_large'].forEach(name =>
    decor(name, 'minecraft:gold_block'))
  ;['copper', 'brass'].forEach(name => decor(name + '_railing', 'create:' + name + '_casing'))
  event.shapeless('4x design_decor:copper_lamp', ['create:copper_casing', 'minecraft:redstone_lamp'])
    .id(industry + 'construction/copper_lamp')
  if (!Platform.isLoaded('create_things_and_misc')) {
    ;['slab', 'stairs'].forEach(shape =>
      event.stonecutting(Item.of('create_things_and_misc:brass_brick_' + shape, 2), 'create_things_and_misc:brass_bricks')
        .id(industry + 'construction/brass_brick_' + shape))
  }
})
