ServerEvents.tags('item', event => {
  event.add('create:backtanks', ['create:copper_backtank', 'create:netherite_backtank'])
  event.add('create:diving_helmets', ['create:copper_diving_helmet', 'create:netherite_diving_helmet'])
  event.add('c:plates/silicon', 'ae2:printed_silicon')
  event.add('cmi:peat_gen', ['cmi:peat_block', 'cmi:peat'])
  event.add('constructionwand:wand', [
    'constructionwand:stone_wand', 'constructionwand:iron_wand',
    'constructionwand:diamond_wand', 'constructionwand:infinity_wand'
  ])
  event.add('ad_astra:fluid_pipes', ['ad_astra:desh_fluid_pipe', 'ad_astra:ostrum_fluid_pipe'])
  event.add('trashcans:trash_cans', [
    'trashcans:item_trash_can', 'trashcans:liquid_trash_can',
    'trashcans:energy_trash_can', 'trashcans:ultimate_trash_can'
  ])
})
