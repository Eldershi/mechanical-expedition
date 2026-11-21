// priority: -100
ServerEvents.recipes(event => {
  const andesite = 'cmi:andesite_mechanism'
  const bronze = 'cmi:bronze_mechanism'
  const coil = 'cmi:coil_mechanism'
  const nuclear = 'cmi:nuclear_mechanism'
  const computing = 'cmi:computing_mechanism'
  const airtight = 'cmi:air_tight_mechanism'
  const antimatter = 'cmi:antimatter_mechanism'
  const tierPart = tier => 'cmi:' + tier + '_mekanism_mechanism'
  const basic = tierPart('basic')
  const advanced = tierPart('advanced')
  const elite = tierPart('elite')
  const ultimate = tierPart('ultimate')

  event.shapeless(andesite, [
    '#c:plates/andesite_alloy', 'create:cogwheel', 'create:large_cogwheel', 'cmi:mechanical_mechanism_part'
  ]).id('expedition:factory/mechanisms/andesite')
  event.shaped('expedition_rock_generator:rock_generator', ['M', 'C', 'P'], {
    M: andesite, C: 'create:andesite_casing', P: 'minecraft:piston'
  }).id('expedition:factory/rock_generator')

  const applyParts = (id, placements) => {
    let found = false
    event.forEachRecipe({id: id}, recipe => {
      found = true
      const original = JSON.parse(String(recipe.originalJson))
      const automatic = placements[0].length === 1
      if (automatic && original.ingredients && !original.pattern && original.ingredients.length < 9) {
        recipe.merge({ingredients: original.ingredients.concat({item: placements[0][0]})})
        return
      }

      const rows = original.pattern.map(row => row.split(''))
      const key = original.key
      let slots = placements
      if (automatic) {
        const part = placements[0][0]
        const available = rows.findIndex(row => row.includes(' '))
        if (available >= 0) slots = [[part, available, rows[available].indexOf(' ')]]
        else if (rows.length < 3) {
          rows.unshift(rows[0].map(() => ' '))
          slots = [[part, 0, 0]]
        } else {
          const cells = rows.reduce((cells, row) => cells.concat(row), [])
          const repeated = cells.find(symbol => cells.indexOf(symbol) !== cells.lastIndexOf(symbol))
          if (!repeated) throw new Error('Choose an ingredient slot for ' + id)
          const index = cells.indexOf(repeated)
          slots = [[part, Math.floor(index / rows[0].length), index % rows[0].length]]
        }
      }

      slots.forEach(([part, row, column]) => {
        const token = ['m', 'k', 'g', 'y'].find(letter => !key[letter])
        if (!token) throw new Error('No free ingredient symbol for ' + id)
        if (!rows[row] || rows[row][column] === undefined) throw new Error('Invalid ingredient slot for ' + id)
        rows[row][column] = token
        key[token] = {item: part}
      })
      const pattern = rows.map(row => row.join(''))
      Object.keys(key).forEach(symbol => {
        if (!pattern.some(row => row.includes(symbol))) delete key[symbol]
      })
      recipe.merge({pattern: pattern, key: key})
    })
    if (!found) throw new Error('Missing equipment recipe ' + id)
  }

  const requireParts = (namespace, part, recipes) =>
    recipes.forEach(id => applyParts(namespace + ':' + id, [[part]]))

  // Early chemical machines can be built before the first Mekanism mechanism.
  requireParts('mekanism', andesite, [
    'electric_pump', 'chemical_oxidizer', 'chemical_infuser', 'rotary_condensentrator'
  ])
  requireParts('mekanism', coil, ['metallurgic_infuser', 'enrichment_chamber', 'supercharged_coil'])
  requireParts('mekanism', basic, [
    'crusher', 'combiner', 'energized_smelter', 'precision_sawmill', 'fuelwood_heater', 'fluidic_plenisher',
    'formulaic_assemblicator', 'logistical_sorter', 'oredictionificator', 'painting_machine', 'pigment_extractor',
    'pigment_mixer', 'nutritional_liquifier', 'bin/basic', 'energy_cube/basic', 'chargepad',
    'boiler_valve', 'pressure_disperser'
  ])
  requireParts('mekanism', advanced, [
    'osmium_compressor', 'purification_chamber', 'chemical_injection_chamber',
    'seismic_vibrator', 'resistive_heater', 'laser', 'laser_amplifier', 'laser_tractor_beam'
  ])
  requireParts('mekanism', elite, [
    'chemical_dissolution_chamber', 'chemical_washer', 'chemical_crystallizer', 'solar_neutron_activator',
    'digital_miner', 'dimensional_stabilizer'
  ])
  requireParts('mekanism', ultimate, ['quantum_entangloporter', 'teleporter', 'modification_station'])
  requireParts('mekanism', airtight, ['pressurized_reaction_chamber'])
  requireParts('mekanism', computing, [
    'qio_drive_base', 'qio_dashboard', 'thermal_evaporation/controller'
  ])
  requireParts('mekanism', nuclear, ['isotopic_centrifuge'])
  requireParts('mekanism', antimatter, ['antiprotonic_nucleosynthesizer'])

  const tiers = ['basic', 'advanced', 'elite', 'ultimate']
  const factories = ['combining', 'compressing', 'crushing', 'enriching', 'infusing',
    'injecting', 'purifying', 'sawing', 'smelting']
  tiers.forEach(tier => {
    const part = tierPart(tier)
    const ids = factories.map(name => 'factory/' + tier + '/' + name).concat('tier_installer/' + tier)
    if (tier !== 'basic') ids.push('bin/' + tier, 'energy_cube/' + tier)
    requireParts('mekanism', part, ids)
  })

  // Keep basic power available before electrical fabrication.
  requireParts('mekanismgenerators', andesite, ['generator/heat'])
  requireParts('mekanismgenerators', coil, [
    'generator/bio', 'generator/wind', 'generator/advanced_solar', 'electromagnetic_coil'
  ])
  requireParts('mekanismgenerators', computing, ['fission_reactor/logic_adapter'])
  applyParts('mekanismgenerators:generator/solar', [[basic, 1, 1]])
  applyParts('mekanismgenerators:generator/gas_burning', [[coil, 0, 1]])
  applyParts('mekanismgenerators:reactor/controller', [[nuclear, 2, 0], [computing, 2, 2]])

  applyParts('createdieselgenerators:crafting/diesel_engine', [[bronze, 0, 1]])
  event.remove({id: 'createdieselgenerators:crafting/huge_diesel_engine'})
  requireParts('steampowered', bronze, ['furnace_engine'])
  applyParts('steampowered:alternator', [[coil, 1, 2]])
  ;['bronze', 'cast_iron', 'steel'].forEach(metal => event.remove({id: 'steampowered:' + metal + '_steam_engine'}))

  applyParts('createaddition:mechanical_crafting/alternator', [[coil, 0, 2]])
  applyParts('createaddition:mechanical_crafting/electric_motor', [[coil, 0, 2]])
  applyParts('createaddition:crafting/modular_accumulator', [[coil, 1, 1]])
  event.remove({id: 'createaddition:crafting/portable_energy_interface'})
  event.remove({id: 'createaddition:mechanical_crafting/tesla_coil'})

  applyParts('powergrid:mechanical_crafting/electric_motor', [[coil, 3, 2]])
  applyParts('powergrid:mechanical_crafting/generator_commutator', [[coil, 3, 1]])
  applyParts('powergrid:crafting/hv_breaker', [['powergrid:electrical_gizmo', 0, 1]])

  applyParts('createnuclear:mechanical_crafting/reactor_controller', [[nuclear, 2, 0], [computing, 2, 4]])
  applyParts('createnuclear:mechanical_crafting/reactor_core', [[nuclear, 2, 1]])
  event.remove({id: 'createnuclear:mixing/steel'})
})
