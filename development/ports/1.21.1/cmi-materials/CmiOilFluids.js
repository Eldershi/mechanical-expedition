StartupEvents.registry('fluid', event => {
  const fluids = {
    conditioned_crude_oil: ['Conditioned Crude Oil', 0x51382D],
    bitumen: ['Bitumen', 0x302824],
    sulfric_diesel: ['Sulfurous Diesel', 0xFFDA69],
    kerosene: ['Kerosene', 0xFF6F6F],
    naphtha: ['Naphtha', 0xE8BD66],
    cracked_gasoline: ['Cracked Gasoline', 0xFF6F6F],
    benzene: ['Benzene', 0xFFF4AD],
    light_olefin: ['Light Olefins', 0x6FEAFF],
    phenol: ['Phenol', 0xFFD46F]
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
