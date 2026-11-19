StartupEvents.registry('fluid', event => {
  const syrup = event.create('cmi:sugar_syrup')
    .displayName('Sugar Syrup')
    .flowingTexture('cmi:fluid/organic/flow')
    .stillTexture('cmi:fluid/organic/still')
    .tint(0xBD702A)
    .translucent()
  syrup.bucketItem.tag('cmi:buckets')
})
