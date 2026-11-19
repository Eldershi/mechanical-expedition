StartupEvents.registry('fluid', event => {
  const colors = {
    andesite_alloy: 0xC7C8B8,
    aluminum_alloy: 0xCAD4E4,
    calorite: 0xD45D4F,
    cast_iron: 0x454545,
    desh: 0xC4713F,
    dreamcore: 0xEE8ED7,
    industrial_iron: 0x626262,
    mechanium: 0xBCDAF8,
    ostrum: 0xAA83A9,
    refined_radiance: 0xEEE8F8,
    titanium: 0xC6DBD8,
    titanium_alloy: 0xA1C8CC,
    tungsten_steel: 0x4A5660
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
