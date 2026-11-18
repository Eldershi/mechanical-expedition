StartupEvents.registry('block', event => {
  const masonry = {
    kaolinite: 'cmi:block/kaolinite_block',
    refractory_grout: 'cmi:block/refractory_grout'
  }
  Object.keys(masonry).forEach(name => {
    event.create(`cmi:${name}`)
      .texture(masonry[name])
      .soundType(SoundType.GRAVEL)
      .hardness(0.5)
      .resistance(0.5)
      .tagBlock('minecraft:mineable/shovel')
  })
})

StartupEvents.registry('item', event => {
  event.create('immersiveindustry:refractory_kiln_brick')
    .texture('minecraft:item/brick')
    .color(0, 0xC5B093)
})

StartupEvents.registry('fluid', event => {
  const acid = event.create('cmi:nitric_acid')
    .flowingTexture('cmi:fluid/chemical/flow')
    .stillTexture('cmi:fluid/chemical/still')
    .tint(0xD6B000)
    .translucent()
    .tag('cmi:nitric_acid')
  acid.bucketItem.tag('cmi:buckets')
})
