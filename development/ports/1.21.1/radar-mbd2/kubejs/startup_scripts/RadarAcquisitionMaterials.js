StartupEvents.registry('block', event => {
  event.create('cmi:smart_casing')
    .parentModel('cmi:block/casing/ae2/smart')
    .soundType(SoundType.METAL)
    .hardness(5)
    .resistance(5)
    .tag('create:casing')
    .tagBlock('create:wrench_pickup')
    .tagBlock('minecraft:mineable/pickaxe')
    .tagBlock('minecraft:needs_iron_tool')
})

StartupEvents.registry('item', event => {
  for (const [material, color] of [['stainless_steel', 0xB6BBC4], ['aluminum_alloy', 0x9FC5DC]]) {
    event.create('cmi:' + material + '_plate')
      .texture('cmi:item/material/color/plate/plate')
      .color(0, color)
      .tag('c:plates')
      .tag('c:plates/' + material)
  }
  event.create('cmi:manyullyn_gear')
    .texture('cmi:item/material/color/gear/gear')
    .color(0, 0x956FB4)
    .tag('c:gears')
    .tag('c:gears/manyullyn')
})

StartupEvents.registry('fluid', event => {
  for (const [material, color] of [['etrium', 0x49C677], ['fluix', 0xA779F2]]) {
    const fluid = event.create('cmi:molten_' + material)
      .flowingTexture('cmi:fluid/metal/flow')
      .stillTexture('cmi:fluid/metal/still')
      .tint(color)
      .translucent()
      .tag('c:molten_materials')
      .tag('c:molten_' + material)
    fluid.bucketItem.tag('cmi:buckets')
  }
})
