StartupEvents.registry('block', event => {
  const ores = [
    { name: 'certus_quartz', hardness: 3, tier: 'iron', deepslate: true },
    { name: 'dreamcore_crystal', hardness: 3, tier: null, deepslate: false },
    { name: 'etrium', hardness: 5, tier: 'diamond', deepslate: true }
  ]
  ores.forEach(ore => {
    const rockTypes = ore.deepslate ? ['stone', 'deepslate'] : ['stone']
    rockTypes.forEach(rock => {
      const id = rock === 'stone' ? `${ore.name}_ore` : `deepslate_${ore.name}_ore`
      const hardness = ore.hardness + (rock === 'deepslate' ? 1.5 : 0)
      const block = event.create(`cmi:${id}`)
        .soundType(rock === 'stone' ? SoundType.STONE : SoundType.DEEPSLATE)
        .hardness(hardness)
        .resistance(hardness)
        .requiresTool()
        .tagBlock('minecraft:mineable/pickaxe')
        .tagBoth('cmi:ores')
        .tagBoth('c:ores')
        .tagBoth(`c:ores/${ore.name}`)
      if (ore.tier) block.tagBlock(`minecraft:needs_${ore.tier}_tool`)
      if (ore.name === 'etrium') {
        block.defaultCutout()
        block.color(0, 0x32FFD4)
        block.item(item => item.color(0, 0x32FFD4))
        block.parentModel('nebula_libs:block/ore/simple_double_layered')
        block.textures({
          background: `minecraft:block/${rock}`,
          ore: 'cmi:block/ore/assets/ore_11',
          particle: 'cmi:block/ore/assets/ore_11'
        })
      } else {
        block.texture(`cmi:block/ore/${ore.name}/${rock}`)
      }
    })
  })
})

StartupEvents.registry('item', event => {
  event.create('cmi:raw_etrium')
    .texture('cmi:item/material/raw/etrium')
    .tag('cmi:raw_metals')
    .tag('c:raw_materials')
    .tag('c:raw_materials/etrium')
})
