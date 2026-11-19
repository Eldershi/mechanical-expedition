ServerEvents.recipes(event => {
  const path = 'expedition:factory/foundry/'
  const metals = [
    ['desh', 'cmi:molten_desh', 'ad_astra:desh_ingot', 2250, ['gear']],
    ['ostrum', 'cmi:molten_ostrum', 'ad_astra:ostrum_ingot', 2425, ['gear']],
    ['calorite', 'cmi:molten_calorite', 'ad_astra:calorite_ingot', 2600, ['gear']],
    ['refined_radiance', 'cmi:molten_refined_radiance', 'create:refined_radiance', 2106, []],
    ['titanium', 'cmi:molten_titanium', 'cmi:titanium_ingot', 1900, ['ingot', 'plate']],
    ['titanium_alloy', 'cmi:molten_titanium_alloy', 'cmi:titanium_alloy_ingot', 2050, ['ingot', 'plate']],
    ['aluminum_alloy', 'cmi:molten_aluminum_alloy', 'neoecoae:aluminum_alloy_ingot', 780, ['plate']],
    ['tungsten_steel', 'cmi:molten_tungsten_steel', 'cmi:tungsten_steel_plate', 2350, ['plate', 'gear']],
    ['tungsten', 'modernfoundry:molten_tungsten', null, 0, ['plate']],
    ['chromium', 'modernfoundry:molten_chromium', null, 0, ['ingot']],
    ['stainless_steel', 'cmi:molten_stainless_steel', null, 0, ['ingot', 'plate']]
  ]

  metals.forEach(([metal, fluid, solid, temperature, forms]) => {
    if (solid) {
      var meltId = path + 'melt_' + metal
      event.custom({
        type: 'modernfoundry:melting',
        id: meltId,
        ingredient: { item: solid },
        result: { fluid: fluid, amount: 90 },
        temperature: temperature,
        time: 100
      }).id(meltId)
    }
    forms.forEach(form => {
      var amount = form === 'gear' ? 360 : 90
      var result = `cmi:${metal}_${form}`
      ;['single_use', 'multi_use'].forEach(usage => {
        var castId = path + `cast_${metal}_${form}_${usage}`
        event.custom({
          type: 'modernfoundry:casting_table',
          id: castId,
          cast: { tag: `modernfoundry:casts/${usage}/${form}` },
          cast_consumed: usage === 'single_use',
          fluid: { fluid: fluid, amount: amount },
          result: { item: result },
          cooling_time: form === 'gear' ? 150 : 60
        }).id(castId)
      })
    })
  })
})
