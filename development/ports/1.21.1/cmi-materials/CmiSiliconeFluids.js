StartupEvents.registry('fluid', event => {
  const fluids = {
    vinegar: ['Vinegar', 0xFAF3E0],
    vinegar_acid: ['Acetic Acid', 0xE7FFF3],
    light_silicone_ether: ['Light Silicone Ether', 0xD4CFE8],
    polysilicone_ether: ['Polysilicone Ether', 0xB0A8D1],
    silicon_rubber: ['Liquid Silicone Rubber', 0xC7C7D2]
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
