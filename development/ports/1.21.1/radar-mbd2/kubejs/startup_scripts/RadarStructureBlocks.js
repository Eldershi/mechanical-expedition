StartupEvents.registry('block', event => {
  const components = ['radar', 'transformer', 'modem', 'tracking_array', 'power_supply']
  components.forEach(part => {
    const block = event.create('cmi:' + part).unbreakable().waterlogged()
    const damaged = event.create('cmi:broken_' + part).unbreakable().waterlogged()
    if (part === 'radar') {
      block.box(6, 0, 6, 10, 16, 10, true)
      damaged.box(6, 0, 6, 10, 16, 10, true)
    }
    block.parentModel('cmi:block/radar/normal/' + part)
    damaged.parentModel('cmi:block/radar/broken/' + part)
  })
  for (const color of ['light_gray', 'white']) {
    event.create('cmi:' + color + '_reinforced_concrete').hardness(50)
      .resistance(3600000).noDrops().parentModel('minecraft:block/' + color + '_concrete')
  }
})
