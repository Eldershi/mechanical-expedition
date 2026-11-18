StartupEvents.registry('fluid', event => {
  const colors = {
    andesite_alloy: 0xC7C8B8,
    dreamcore: 0xEE8ED7,
    mechanium: 0xBCDAF8
  }
  Object.keys(colors).forEach(name => {
    const fluid = event.create(`cmi:molten_${name}`)
      .flowingTexture('cmi:fluid/metal/flow')
      .stillTexture('cmi:fluid/metal/still')
      .tint(colors[name])
      .translucent()
      .tag('c:molten_materials')
      .tag(`c:molten_${name}`)
    fluid.bucketItem.tag('cmi:buckets')
  })
})
