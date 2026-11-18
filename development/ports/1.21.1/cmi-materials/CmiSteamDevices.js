StartupEvents.registry('block', event => {
  const tiers = {
    cast_iron: [38, 24, 16000, 32768],
    steel: [75, 48, 32000, 65536]
  }
  Object.keys(tiers).forEach(tier => {
    const stats = tiers[tier]
    const material = `steam_letters:${tier}`
    event.create(`cmi:${tier}_solar_boiler`, 'steam_letters:solar')
      .material(material).production(stats[0]).capacity(stats[2])
    event.create(`cmi:${tier}_boiler`, 'steam_letters:boiler')
      .material(material).production(stats[1]).capacity(stats[2])
    event.create(`cmi:${tier}_solid_burner`, 'steam_letters:solid_burner').material(material)
    event.create(`cmi:${tier}_fluid_burner`, 'steam_letters:fluid_burner').material(material)
    event.create(`cmi:${tier}`, 'steam_letters:engine_and_flywheel')
      .material(material).strength(stats[3]).speed(32).consumption(stats[1]).capacity(stats[2])
  })
})
