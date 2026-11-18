StartupEvents.registry('block', event => {
  event.create('cmi:osmium_tile')
    .displayName('Osmium Tile')
    .texture('cmi:block/osmium_tile')
    .soundType(SoundType.METAL)
    .hardness(5)
    .resistance(6)
    .tagBlock('minecraft:mineable/pickaxe')
})

StartupEvents.registry('fluid', event => {
  const fluids = {
    cracked_diesel: ['Cracked Diesel', 0xDDCCBB],
    light_aldehyde: ['Light Aldehydes', 0xAACCFF],
    acetylene: ['Acetylene', 0xDADEDF],
    vinyl_alcohol: ['Vinyl Alcohol', 0x9988AA],
    polyvinyl_alcohol: ['Polyvinyl Alcohol', 0x887799],
    structural_plastic: ['Structural Plastic', 0xAABBEE]
  }
  Object.keys(fluids).forEach(key => {
    const [name, color] = fluids[key]
    const fluid = event.create(`cmi:${key}`)
      .displayName(name)
      .flowingTexture('cmi:fluid/organic/flow')
      .stillTexture('cmi:fluid/organic/still')
      .tint(color)
      .translucent()
      .tag(`cmi:${key}`)
    fluid.bucketItem.tag('cmi:buckets')
  })
})
