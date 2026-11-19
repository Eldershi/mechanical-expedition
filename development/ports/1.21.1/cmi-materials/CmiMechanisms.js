StartupEvents.registry('item', event => {
  const finished = [
    'copper', 'bronze', 'iron', 'nether', 'ender',
    'railway', 'coil', 'light_engineering', 'heavy_engineering', 'smart',
    'photosensitive', 'basic_mekanism', 'advanced_mekanism',
    'elite_mekanism', 'ultimate_mekanism', 'computing', 'air_tight', 'aeronautic', 'nuclear',
    'astronautic', 'antimatter', 'creative'
  ]

  finished.forEach(name => {
    event.create(`cmi:incomplete_${name}_mechanism`, 'create:sequenced_assembly')
      .texture(`cmi:item/mechanism/incomplete/${name}`)
      .tag('cmi:incomplete_mechanisms')
      .tag('cmi:incomplete_items')
  })

  finished.forEach(name => {
    event.create(`cmi:${name}_mechanism`)
      .texture(`cmi:item/mechanism/complete/${name}`)
      .tag('cmi:mechanisms')
      .tag(`cmi:mechanisms/${name}`)
  })
})
