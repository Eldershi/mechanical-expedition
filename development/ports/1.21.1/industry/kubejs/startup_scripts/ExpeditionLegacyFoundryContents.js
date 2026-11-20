StartupEvents.registry('fluid', event => {
  event.create('thermal:redstone')
    .displayName('Destabilized Redstone')
    .stillTexture('cmi:fluid/metal/still')
    .flowingTexture('cmi:fluid/metal/flow')
    .tint(0xDE242A)
})

StartupEvents.registry('item', event => {
  event.create('terramity:fairy_dust')
    .displayName('Fairy Dust')
    .texture('minecraft:item/glowstone_dust')
})
