StartupEvents.registry('block', event => {
  event.create('expedition_space:riveted_frame').texture('minecraft:block/exposed_copper')
    .hardness(3).resistance(6)
  event.create('expedition_space:structural_panel').texture('minecraft:block/polished_deepslate')
    .hardness(3).resistance(6)
  event.create('expedition_space:insulated_window').texture('minecraft:block/tinted_glass')
    .hardness(1).resistance(3)
  event.create('expedition_space:surface_beacon').texture('minecraft:block/sea_lantern')
    .hardness(3).resistance(6)
})

StartupEvents.registry('item', event => {
  const space = 'expedition_space:'
  event.create(space + 'freight_remote').texture('minecraft:item/compass_00').maxStackSize(1)
  event.create(space + 'freight_module').texture('minecraft:item/minecart').maxStackSize(1)
  event.create(space + 'lunar_signature').texture('minecraft:item/echo_shard').maxStackSize(1)
  event.create(space + 'life_support_module').texture('minecraft:item/spyglass').maxStackSize(1)
  event.create(space + 'thermal_lining').texture('minecraft:item/magma_cream').maxStackSize(1)
})
