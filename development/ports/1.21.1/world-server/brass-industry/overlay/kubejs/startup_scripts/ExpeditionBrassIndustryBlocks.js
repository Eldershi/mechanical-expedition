StartupEvents.registry('block', event => {
  const states = Java.loadClass('net.minecraft.world.level.block.state.properties.BlockStateProperties')
  const directions = Java.loadClass('net.minecraft.core.Direction')
  const texture = 'create:block/'
  const blocks = {
    green_container: 'industrial_iron_block', red_container: 'industrial_iron_block',
    industrial_gear: 'industrial_iron_block', industrial_gear_large: 'industrial_iron_block',
    ochrum_crushing_wheel: 'industrial_iron_block', crushing_wheel_controller: 'andesite_casing',
    copper_lamp: 'copper_casing', industrial_gold_block: 'brass_casing',
    gold_boiler: 'brass_casing', gold_boiler_large: 'brass_casing', gold_boiler_structure: 'brass_casing'
  }
  Object.entries(blocks).forEach(([name, skin]) => {
    const block = event.create('design_decor:' + name).texture(texture + skin).hardness(3)
    if (name === 'industrial_gear' || name === 'industrial_gear_large') {
      block.property(states.AXIS).placementState(p => p.setValue(states.AXIS, p.getClickedFace().getAxis()))
        .rotateState(s => {
          const axis = s.getValue(states.AXIS)
          const facing = axis.getName() === 'x' ? directions.EAST : axis.getName() === 'z' ? directions.SOUTH : directions.UP
          s.setValue(states.AXIS, s.rotate(facing).getAxis())
        })
    }
    if (name === 'copper_lamp') {
      block.lightLevel(0.85).property(states.FACING)
        .placementState(p => p.setValue(states.FACING, p.getClickedFace()))
        .rotateState(s => s.setValue(states.FACING, s.rotate(s.getValue(states.FACING))))
    }
  })
  ;['brass', 'copper'].forEach(metal => {
    event.create('design_decor:' + metal + '_railing', 'fence').texture(texture + metal + '_casing')
  })
  if (!Platform.isLoaded('create_things_and_misc')) {
    event.create('create_things_and_misc:brass_brick_slab', 'slab').texture(texture + 'brass_casing')
    event.create('create_things_and_misc:brass_brick_stairs', 'stairs').texture(texture + 'brass_casing')
  }
})
