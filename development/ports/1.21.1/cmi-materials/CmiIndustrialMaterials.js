StartupEvents.registry('item', event => {
  const materials = {
    cast_iron: [0x454545, 'ingot', 'dust', 'plate'],
    stainless_steel: [0x647280, 'ingot'],
    chromium: [0xEBE3E4, 'ingot', 'dust'],
    vanadium: [0x4D4383, 'dust'],
    pure_quartz: [0xA5F1FF, 'dust', 'prism'],
    wooden: [0xAB7500, 'gear'],
    andesite_alloy: [0xC7C8B8, 'plate']
  }
  Object.keys(materials).forEach(material => {
    const forms = materials[material]
    forms.slice(1).forEach(form => {
      event.create(`cmi:${material}_${form}`)
        .texture(`cmi:item/material/color/${form}/${form}`)
        .color(0, forms[0])
        .tag(`c:${form}s`)
        .tag(`c:${form}s/${material}`)
    })
  })
})
