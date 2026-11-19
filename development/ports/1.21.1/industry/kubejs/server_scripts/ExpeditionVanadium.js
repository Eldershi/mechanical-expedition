ServerEvents.recipes(event => {
  const path = 'expedition:factory/vanadium/'
  const ingot = 'vintageimprovements:vanadium_ingot'
  event.blasting(ingot, 'cmi:raw_vanadium').xp(0.7).id(path + 'blasting')
  event.recipes.create.pressing('vintageimprovements:vanadium_sheet', ingot).id(path + 'pressing')
  event.recipes.create.milling('cmi:vanadium_dust', Ingredient.of('#c:ingots/vanadium')).id(path + 'mill_ingot')
})
