StartupEvents.registry('item', event => {
  const assemblyOnly = [
    'wooden', 'stone', 'gold'
  ]
  const finished = [
    'copper', 'bronze', 'iron', 'pig_iron', 'colorful', 'enchanted', 'nether', 'sculk', 'ender',
    'andesite', 'nature', 'potion', 'railway', 'coil', 'light_engineering', 'heavy_engineering', 'smart',
    'cobalt', 'photosensitive', 'reinforced', 'basic_mekanism', 'advanced_mekanism',
    'elite_mekanism', 'ultimate_mekanism', 'computing', 'air_tight', 'aeronautic', 'nuclear',
    'astronautic', 'antimatter', 'creative'
  ]

  assemblyOnly.concat(finished).forEach(name => {
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
