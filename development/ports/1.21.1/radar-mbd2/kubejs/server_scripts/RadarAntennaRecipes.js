ServerEvents.recipes(event => {
  const powers = [1000000, 2000000, 5000000, 10000000]
  let input = 'cmi:empty_cell'
  powers.forEach((power, index) => {
    const tier = index + 1
    const output = 'cmi:tier_' + tier + '_aviation_cell'
    event.recipes.cmi.radar_antenna()
      .inputItems(input).inputFE(power).outputItems(output)
      .id('expedition:radar/aviation_cell_' + tier)
    input = output
  })
})
