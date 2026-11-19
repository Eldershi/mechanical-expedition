StartupEvents.registry('fluid', event => {
  const colors = {
    sea_water: 0x537D98,
    concentrated_sea_water: 0x435B8B,
    brine: 0xA3A189,
    alkaline_brine: 0x8FA8A4,
    waste_brine: 0x3C3C3C,
    bromine: 0x9B3429,
    lithium_containing_electrolyte: 0x555100,
    caustic_soda_solution: 0xB8D1B6,
    crystal_catalyt: 0x90EE90,
    chromium_solution: 0xEBE3E4,
    radiation_resistant_creosote: 0x8B2929,
    radon: 0x00FF00
  }
  Object.keys(colors).forEach(name => {
    const fluid = event.create(`cmi:${name}`)
      .flowingTexture('cmi:fluid/chemical/flow')
      .stillTexture('cmi:fluid/chemical/still')
      .tint(colors[name])
      .translucent()
      .tag(`cmi:${name}`)
    fluid.bucketItem.tag('cmi:buckets')
  })
})
