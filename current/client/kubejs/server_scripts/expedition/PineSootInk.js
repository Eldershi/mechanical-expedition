// priority: -1401
// Traditional soot-and-hide-glue ink, represented with existing pack materials.
// Keep all existing ink recipes and item/fluid registrations unchanged.
ServerEvents.recipes(event => {
  event.custom({
    type: 'create:mixing',
    heatRequirement: 'heated',
    processingTime: 200,
    ingredients: [
      { item: 'mekanism:dust_charcoal' },
      { item: 'mekanism:dust_charcoal' },
      { item: 'minecraft:leather' },
      { fluid: 'minecraft:water', amount: 1000 }
    ],
    results: [{ fluid: 'irons_spellbooks:common_ink', amount: 1000 }]
  }).id('expedition:pine_ink/prepare_common_ink')
})

ServerEvents.afterRecipes(event => {
  const report = {
    id: 'expedition:pine_ink/prepare_common_ink',
    count: event.countRecipes({ id: 'expedition:pine_ink/prepare_common_ink' }),
    nativeBottlingCount: event.countRecipes({ id: 'irons_spellbooks:create_compat/create_fill_common_ink' }),
    nativeEmptyingCount: event.countRecipes({ id: 'irons_spellbooks:create_compat/create_empty_common_ink' }),
    charcoalDustPresent: Item.exists('mekanism:dust_charcoal'),
    commonInkPresent: Item.exists('irons_spellbooks:common_ink')
  }
  report.passed = report.count === 1 && report.nativeBottlingCount === 1 &&
    report.nativeEmptyingCount === 1 && report.charcoalDustPresent && report.commonInkPresent
  JsonIO.write('kubejs/exported/expedition-pine-soot-ink.json', report)
  console.info('[Pine Soot Ink] recipes=' + report.count + ' nativeBottling=' +
    report.nativeBottlingCount + ' passed=' + report.passed)
})
