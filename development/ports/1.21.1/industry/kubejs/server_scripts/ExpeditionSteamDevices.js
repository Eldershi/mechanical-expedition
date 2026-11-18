ServerEvents.recipes(event => {
  const tiers = [
    ['bronze', 'steam_letters', 'modernfoundry:seared_bricks'],
    ['cast_iron', 'cmi', 'modernfoundry:scorched_bricks'],
    ['steel', 'cmi', 'immersiveengineering:blastbrick']
  ]
  tiers.forEach(tier => {
    const material = tier[0]
    const namespace = tier[1]
    const brick = tier[2]
    const plate = `#c:plates/${material}`
    const ingot = `#c:ingots/${material}`
    const metal = [plate, ingot]
    const machine = `${namespace}:${material}`
    const path = `expedition:factory/steam/${material}`
    event.shaped(`${machine}_solar_boiler`, ['ABA', 'ACA', 'DDD'], {
      A: metal, B: '#c:plates/silver', C: 'cmi:bronze_mechanism', D: brick
    }).id(path + '_solar_boiler')
    event.shaped(`${machine}_boiler`, ['AAA', 'ACA', 'ABA'], {
      A: metal, B: 'create:fluid_pipe', C: 'create:fluid_tank'
    }).id(path + '_boiler')
    event.shaped(`${machine}_solid_burner`, ['AAA', 'ABA', 'CCC'], {
      A: metal, B: 'minecraft:furnace', C: brick
    }).id(path + '_solid_burner')
    event.shaped(`${machine}_fluid_burner`, ['AAA', 'ABA', 'CCC'], {
      A: metal, B: 'cmi:copper_mechanism', C: brick
    }).id(path + '_fluid_burner')
    event.shaped(`${machine}_steam_engine`, ['ABE', 'MCF', 'ABE'], {
      A: plate, B: ingot, C: 'steam_letters:bronze_casing', M: 'cmi:bronze_mechanism',
      E: 'create:andesite_alloy', F: 'create:shaft'
    }).id(path + '_engine')
  })
})
