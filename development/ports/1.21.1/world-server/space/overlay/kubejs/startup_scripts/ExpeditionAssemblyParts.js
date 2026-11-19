// These legacy identifiers preserve the block requirements of the assembly patterns.
StartupEvents.registry('block', event => {
  const states = Java.loadClass('net.minecraft.world.level.block.state.properties.BlockStateProperties')
  const bool = Java.loadClass('net.minecraft.world.level.block.state.properties.BooleanProperty')
  const facingUp = bool.create('facing_up')
  const decor = {
    andesite_floodlight: 'andesite_casing',
    brass_lamp: 'brass_casing',
    brass_boiler: 'brass_casing',
    brass_boiler_large: 'brass_casing',
    brass_boiler_structure: 'brass_casing',
    cast_iron_boiler: 'industrial_iron_block',
    cast_iron_boiler_large: 'industrial_iron_block',
    cast_iron_boiler_structure: 'industrial_iron_block',
    copper_boiler: 'copper_casing',
    diagonal_girder: 'industrial_iron_block',
    diagonal_metal_support: 'industrial_iron_block',
    industrial_iron_boiler: 'industrial_iron_block',
    industrial_iron_boiler_large: 'industrial_iron_block',
    industrial_iron_boiler_structure: 'industrial_iron_block',
    industrial_plating_block: 'industrial_iron_block',
    metal_support: 'industrial_iron_block',
    ornate_grate: 'industrial_iron_block'
  }
  Object.entries(decor).forEach(([id, texture]) => {
    const block = event.create('design_decor:' + id).texture('create:block/' + texture)
      .hardness(3).resistance(6)
    if (id === 'brass_lamp' || id === 'andesite_floodlight') block.lightLevel(0.85)
    if (['industrial_iron_boiler', 'copper_boiler', 'brass_lamp', 'andesite_floodlight'].includes(id)) {
      block.property(states.FACING).placementState(placement => {
        placement.setValue(states.FACING, placement.getClickedFace())
      }).rotateState(state => {
        state.setValue(states.FACING, state.rotate(state.getValue(states.FACING)))
      })
    } else if (id === 'diagonal_girder') {
      block.property(states.HORIZONTAL_FACING).property(facingUp).placementState(placement => {
        placement.setValue(states.HORIZONTAL_FACING, placement.getHorizontalDirection())
        placement.set(facingUp, placement.getClickedFace().getName() === 'up' || placement.isSecondaryUseActive())
      }).rotateState(state => {
        state.setValue(states.HORIZONTAL_FACING, state.rotate(state.getValue(states.HORIZONTAL_FACING)))
      })
    }
  })
  event.create('design_decor:iron_railing', 'fence').texture('create:block/industrial_iron_block')
    .hardness(3).resistance(6)
  if (!Platform.isLoaded('create_things_and_misc')) {
    event.create('create_things_and_misc:brass_bricks').texture('create:block/brass_casing').hardness(3).resistance(6)
  }
  event.create('expedition_space:carbon_electrode').texture('create:block/industrial_iron_block')
    .hardness(3).resistance(6)
})

StartupEvents.registry('item', event => {
  const textures = {
    tin_hard_disk: 'iron_sheet', aluminum_hard_disk: 'sturdy_sheet', brass_hard_disk: 'brass_sheet',
    electron_tube_computer: 'electron_tube', satellite: 'precision_mechanism',
    lime_circuit_board: 'polished_rose_quartz', light_composite_plate: 'sturdy_sheet',
    carrier_rocket: 'precision_mechanism', efficiency_module: 'brass_hand',
    productivity_module_2: 'brass_hand', electro_hydro_capacitor: 'electron_tube',
    mycetozoan: 'andesite_alloy', unknown_prototype: 'precision_mechanism',
    matrix_2: 'polished_rose_quartz', fluid_mechanism: 'copper_sheet',
    magenta_circuit_board: 'electron_tube',
  }
  Object.entries(textures).forEach(([name, texture]) => {
    const item = event.create('expedition_space:' + name).texture('create:item/' + texture)
    if (name.endsWith('_hard_disk')) item.maxDamage(1024)
  })
  event.create('createandesiteabound:filling_machine').texture('create:item/precision_mechanism')
})
