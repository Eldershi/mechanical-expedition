StartupEvents.registry('fluid', event => {
  const fluids = { liquid_air: 0xB8D8F3, electro_hydro_fluid: 0x80DAE3 }
  Object.entries(fluids).forEach(([name, color]) => {
    event.create('expedition_industry:' + name)
      .stillTexture('minecraft:block/water_still').flowingTexture('minecraft:block/water_flow')
      .tint(color).translucent().noBlock()
  })
})
