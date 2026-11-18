const expeditionStartingTools = [
  'create:wrench', 'create:goggles', 'create:super_glue',
  'tiab:time_in_a_bottle', 'create:stressometer'
]

ItemEvents.rightClicked('cmi:initial_item_kit', event => {
  if (!event.player.isShiftKeyDown()) return
  event.item.shrink(1)
  expeditionStartingTools.forEach(item => event.player.give(Item.of(item)))
  event.cancel()
})
