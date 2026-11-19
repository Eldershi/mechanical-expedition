ServerEvents.recipes(event => {
  const space = 'expedition_space:'
  const material = name => ({ item: space + name })
  const steel = { tag: 'c:storage_blocks/steel' }
  const freshDisk = name => ({
    type: 'neoforge:components',
    items: space + name,
    components: { 'minecraft:damage': 0 }
  })
  const matrix = [[[1, 1], [0, 1]], [[0, 2], [0, 1]], [[1, 0], [0, 1]]]
  const exactMatrix = {
    type: 'neoforge:components',
    items: space + 'matrix_2',
    components: { 'minecraft:custom_data': { RGB: matrix, matrix: matrix } }
  }
  const shaped = (name, count, pattern, key) => {
    event.custom({ type: 'minecraft:crafting_shaped', category: 'misc',
      key: key, pattern: pattern, result: { id: space + name, count: count }
    }).id(space + 'station/' + name)
  }

  // Controller grids and yields follow the corresponding craft in Beta0.8.0ColdFix.
  shaped('satellite_relay', 1, ['DBD', 'EAE', 'FFF'], {
    A: material('electron_tube_computer'), B: material('satellite'),
    D: material('lime_circuit_board'), E: freshDisk('tin_hard_disk'), F: steel
  })
  shaped('freight_launchpad', 1, ['DDD', 'EAE', 'FFF'], {
    A: material('carrier_rocket'), D: material('light_composite_plate'),
    E: freshDisk('brass_hard_disk'), F: steel
  })
  shaped('space_elevator', 1, ['DDD', 'EAE', 'FFF'], {
    A: material('efficiency_module'), D: material('lime_circuit_board'),
    E: freshDisk('brass_hard_disk'), F: material('electro_hydro_capacitor')
  })
  shaped('orbital_drop_cannon', 2, ['DBD', 'EAE', 'DDD'], {
    A: { item: 'createandesiteabound:filling_machine' }, B: material('satellite'),
    D: steel, E: freshDisk('aluminum_hard_disk')
  })
  shaped('other_gate', 1, ['AAA', 'CDC', 'EBE'], {
    A: exactMatrix, B: material('productivity_module_2'), C: material('mycetozoan'),
    D: material('unknown_prototype'), E: material('electro_hydro_capacitor')
  })
  shaped('unknown_prototype', 1, ['BBB', 'BCB', 'BBB'], {
    B: { item: 'minecraft:obsidian' }, C: { item: 'minecraft:ender_eye' }
  })
  event.shapeless(Item.of('createandesiteabound:filling_machine', 4),
    [space + 'fluid_mechanism', space + 'magenta_circuit_board']).id(space + 'filling_machine')

  // These acquisition recipes feed the original controller ingredients from Expedition's industries.
  const source = (name, count, ingredients) => {
    event.shapeless(Item.of(space + name, count), ingredients).id(space + 'materials/' + name)
  }
  source('tin_hard_disk', 1, ['#c:ingots/tin', 'create:electron_tube', 'create:cogwheel'])
  source('aluminum_hard_disk', 1, ['#c:plates/aluminum', 'create:precision_mechanism', space + 'magenta_circuit_board'])
  source('brass_hard_disk', 1, ['create:brass_sheet', 'create:precision_mechanism', space + 'lime_circuit_board'])
  source('lime_circuit_board', 2, ['create:electron_tube', 'mekanism:basic_control_circuit', 'minecraft:lime_dye'])
  source('magenta_circuit_board', 2, ['create:electron_tube', 'mekanism:advanced_control_circuit', 'minecraft:magenta_dye'])
  source('light_composite_plate', 2, ['#c:plates/aluminum', 'cmi:composite_carbon_fiber_plate', 'create:copper_sheet'])
  source('electron_tube_computer', 1, [space + 'tin_hard_disk', space + 'tin_hard_disk',
    'create:electron_tube', 'create:electron_tube', 'create:electron_tube', 'create:precision_mechanism'])
  source('satellite', 1, ['cmi:aeronautic_mechanism', 'cmi:optical_fiber', space + 'light_composite_plate'])
  source('carrier_rocket', 1, ['cmi:aeronautic_mechanism', 'ad_astra:steel_engine', space + 'light_composite_plate',
    space + 'light_composite_plate', 'create:precision_mechanism'])
  source('efficiency_module', 1, ['create:precision_mechanism', space + 'lime_circuit_board', 'cmi:optical_fiber'])
  source('productivity_module_2', 1, [space + 'efficiency_module', 'mekanism:elite_control_circuit', space + 'magenta_circuit_board'])
  source('electro_hydro_capacitor', 4, [space + 'light_composite_plate', 'ad_astra:etrionic_capacitor', 'cmi:tungsten_plate',
    'cmi:tungsten_plate', 'minecraft:slime_ball'])
  source('mycetozoan', 2, ['minecraft:slime_ball', 'minecraft:brown_mushroom', 'minecraft:glow_berries'])
  source('fluid_mechanism', 1, ['create:fluid_pipe', 'create:copper_sheet', 'create:precision_mechanism'])
  event.custom({
    type: 'minecraft:crafting_shaped',
    pattern: ['TTT', 'RCB', 'LLL'],
    key: { T: material('lime_circuit_board'), R: { item: 'minecraft:redstone' },
      C: material('mycetozoan'), B: { item: 'minecraft:blue_dye' }, L: { item: 'minecraft:lime_dye' } },
    result: { id: space + 'matrix_2', count: 3, components: { 'minecraft:custom_data': { RGB: matrix, matrix: matrix } } }
  }).id(space + 'materials/matrix_2')
  source('carbon_electrode', 4, ['cmi:activated_graphite_chunk', 'cmi:activated_graphite_chunk', 'create:iron_sheet'])

  if (!Platform.isLoaded('create_things_and_misc')) {
    event.stonecutting(Item.of('create_things_and_misc:brass_bricks', 4), 'create:brass_casing')
      .id(space + 'construction/brass_bricks')
  }
  const shells = {
    cast_iron_boiler: 'create:industrial_iron_block',
    brass_boiler: 'create:brass_casing',
    copper_boiler: 'create:copper_casing',
    industrial_iron_boiler: 'create:industrial_iron_block',
  }
  Object.entries(shells).forEach(([name, base]) => {
    event.shapeless(Item.of('design_decor:' + name, 4), [base, 'create:fluid_pipe'])
      .id(space + 'construction/' + name)
    if (name !== 'copper_boiler') {
      event.stonecutting(Item.of('design_decor:' + name + '_large', 1), 'design_decor:' + name)
        .id(space + 'construction/' + name + '_large')
      event.stonecutting(Item.of('design_decor:' + name + '_structure', 2), 'design_decor:' + name)
        .id(space + 'construction/' + name + '_structure')
    }
  })
  ;['industrial_plating_block', 'ornate_grate', 'metal_support', 'diagonal_metal_support',
    'diagonal_girder', 'iron_railing'].forEach(name => {
    event.stonecutting(Item.of('design_decor:' + name, 4), 'create:industrial_iron_block')
      .id(space + 'construction/' + name)
  })
  event.shapeless(Item.of('design_decor:andesite_floodlight', 4), ['create:andesite_casing', 'minecraft:redstone_lamp'])
    .id(space + 'construction/andesite_floodlight')
  event.shapeless(Item.of('design_decor:brass_lamp', 4), ['create:brass_casing', 'minecraft:redstone_lamp'])
    .id(space + 'construction/brass_lamp')
})
