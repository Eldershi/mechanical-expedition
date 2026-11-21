RecipeViewerEvents.addInformation('item', event => {
  const keys = ['instructions', 'water', 'ice', 'mod', 'speed']
  event.add('expedition_rock_generator:rock_generator',
    keys.map(key => Text.translate('block.expedition_rock_generator.recipe.' + key)))
})
