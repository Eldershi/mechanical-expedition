StartupEvents.registry('fluid', event => {
  event.create('cmi:molten_pure_silicon')
    .flowingTexture('cmi:fluid/chemical/flow')
    .stillTexture('cmi:fluid/chemical/still')
    .tint(0x182431)
    .noBlock()
    .noBucket()

  const colors = {
    sea_water: 0x537D98,
    concentrated_sea_water: 0x435B8B,
    brine: 0xA3A189,
    alkaline_brine: 0x8FA8A4,
    waste_brine: 0x3C3C3C,
    bromine: 0x9B3429,
    hdpe: 0xE0E7E8,
    lithium_containing_electrolyte: 0x555100,
    caustic_soda_solution: 0xB8D1B6,
    crystal_catalyt: 0x90EE90,
    chromium_solution: 0xEBE3E4,
    radiation_resistant_creosote: 0x8B2929,
    radon: 0x00FF00,
    germanium_solution: 0xCEB58B,
    entro_peroxide_solution: 0x62E3D1,
    delta_unstable_solution: 0x766382,
    molten_azure_neodymium: 0x3C8CC4,
    molten_scarlet_neodymium: 0xC33E62,
    molten_neodymium_mixture: 0xC800FF,
    crystal_etching_solution: 0x364700,
    molten_ionized_entro: 0x009556,
    ionized_entro_solution: 0x00C874,
    molten_silicon_containing_compound: 0x4D4D4D,
    pure_crystal_source: 0xA40058,
    liquid_crystal_entro: 0x9CFF00,
    liquid_crystal_etrium: 0x58ECCD,
    crystal_entro_solution: 0x81B34A,
    polonium_containing_electrolyte: 0x399E7D,
    plutonium_containing_electrolyte: 0x3C8A97,
    polonium_containing_solution: 0x9BE9B8,
    plutonium_containing_solution: 0x86E2FD,
    plutonium_extract_solution: 0x9DEFF1,
    radioactive_acid_solution: 0x052A0B,
    polonium_solution: 0xAEECC5
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

  event.create('cmi:liquid_nitrogen')
    .flowingTexture('cmi:fluid/chemical/flow')
    .stillTexture('cmi:fluid/chemical/still')
    .tint(0xA8CCEE)
    .translucent()
    .noBlock()
    .noBucket()
    .tag('c:nitrogen')
})

StartupEvents.registry('mekanism:chemical', event => {
  event.create('cmi:germanium_precursor').tint(0xCEB58B).gaseous()
  event.create('cmi:entro_peroxide').tint(0x62E3D1).gaseous()
  event.create('cmi:chaotic_void').tint(0x790082)
  event.create('cmi:infuse_osmium').tint(0xA7B8DB)
  event.create('cmi:etrium').tint(0x32FFD4)
})
