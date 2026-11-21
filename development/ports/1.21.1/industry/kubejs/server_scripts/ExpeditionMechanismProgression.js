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

  const requirePart = (id, part, preferredSlot) => {
    let found = false
    event.forEachRecipe({id: id}, recipe => {
      found = true
      const original = JSON.parse(String(recipe.originalJson))
      const ingredient = {item: part}
      if (original.ingredients && !original.pattern && original.ingredients.length < 9) {
        recipe.merge({ingredients: original.ingredients.concat(ingredient)})
        return
      }

      const rows = original.pattern.map(row => row.split(''))
      const key = original.key
      const token = ['m', 'k', 'g', 'y'].find(letter => !key[letter])
      if (!token) throw new Error('No free ingredient symbol for ' + id)

      if (preferredSlot) {
        rows[preferredSlot[0]][preferredSlot[1]] = token
      } else {
        var available = rows.find(row => row.includes(' '))
        if (available) {
          available[available.indexOf(' ')] = token
        } else if (rows.length < 3) {
          rows.unshift(rows[0].map((_, column) => column === 0 ? token : ' '))
        } else {
          var cells = rows.reduce((cells, row) => cells.concat(row), [])
          var repeated = cells.find(symbol => cells.indexOf(symbol) !== cells.lastIndexOf(symbol))
          if (!repeated) throw new Error('Choose an ingredient slot for ' + id)
          var index = cells.indexOf(repeated)
          rows[Math.floor(index / rows[0].length)][index % rows[0].length] = token
        }
      }

      const pattern = rows.map(row => row.join(''))
      Object.keys(key).forEach(symbol => {
        if (!pattern.some(row => row.includes(symbol))) delete key[symbol]
      })
      key[token] = ingredient
      recipe.merge({pattern: pattern, key: key})
    })
    if (!found) throw new Error('Missing equipment recipe ' + id)
  }

  const requireParts = (namespace, part, recipes) => {
    recipes.forEach(id => requirePart(namespace + ':' + id, part))
  }

  // These machines make the chemicals and steel needed for higher construct tiers.
  requireParts('mekanism', andesite, [
    'steel_casing', 'metallurgic_infuser', 'enrichment_chamber', 'electric_pump', 'electrolytic_separator',
    'chemical_oxidizer', 'chemical_infuser', 'rotary_condensentrator', 'fluid_tank/basic', 'chemical_tank/basic'
  ])
  requireParts('mekanism', basic, [
    'crusher', 'combiner', 'energized_smelter', 'precision_sawmill', 'fuelwood_heater', 'fluidic_plenisher',
    'formulaic_assemblicator', 'logistical_sorter', 'oredictionificator', 'painting_machine', 'pigment_extractor',
    'pigment_mixer', 'nutritional_liquifier', 'bin/basic', 'energy_cube/basic', 'chargepad', 'dynamic_tank',
    'dynamic_valve', 'boiler_casing', 'boiler_valve', 'pressure_disperser', 'superheating_element',
    'induction/casing', 'induction/port', 'thermal_evaporation/block', 'thermal_evaporation/controller',
    'thermal_evaporation/valve', 'transmitter/diversion_transporter', 'transmitter/restrictive_transporter'
  ])
  requireParts('mekanism', advanced, [
    'osmium_compressor', 'purification_chamber', 'chemical_injection_chamber', 'pressurized_reaction_chamber',
    'seismic_vibrator', 'resistive_heater', 'laser', 'laser_amplifier', 'laser_tractor_beam'
  ])
  requireParts('mekanism', elite, [
    'chemical_dissolution_chamber', 'chemical_washer', 'chemical_crystallizer', 'solar_neutron_activator',
    'digital_miner', 'dimensional_stabilizer'
  ])
  requireParts('mekanism', ultimate, ['quantum_entangloporter', 'teleporter', 'modification_station'])
  requireParts('mekanism', computing, [
    'qio_drive_base', 'qio_dashboard', 'qio_importer', 'qio_exporter', 'qio_redstone_adapter'
  ])
  requireParts('mekanism', nuclear, ['isotopic_centrifuge', 'radioactive_waste_barrel'])
  requireParts('mekanism', antimatter, ['antiprotonic_nucleosynthesizer'])
  requireParts('mekanism', ultimate, ['sps_port', 'supercharged_coil'])

  const tiers = ['basic', 'advanced', 'elite', 'ultimate']
  const factories = ['combining', 'compressing', 'crushing', 'enriching', 'infusing',
    'injecting', 'purifying', 'sawing', 'smelting']
  const transmitters = ['logistical_transporter', 'mechanical_pipe', 'pressurized_tube',
    'thermodynamic_conductor', 'universal_cable']
  tiers.forEach(tier => {
    const part = tierPart(tier)
    const ids = factories.map(name => 'factory/' + tier + '/' + name)
      .concat(transmitters.map(name => 'transmitter/' + name + '/' + tier))
      .concat(['tier_installer/', 'induction/cell/', 'induction/provider/'].map(path => path + tier))
    if (tier !== 'basic') {
      ids.push('bin/' + tier, 'energy_cube/' + tier, 'fluid_tank/' + tier, 'chemical_tank/' + tier)
    }
    requireParts('mekanism', part, ids)
  })

  // Keep basic power available before electrical fabrication.
  requireParts('mekanismgenerators', andesite, ['generator/heat'])
  requireParts('mekanismgenerators', basic, ['generator/bio', 'generator/solar'])
  requireParts('mekanismgenerators', coil, [
    'generator/wind', 'generator/advanced_solar', 'generator/gas_burning',
    'turbine/rotor', 'rotational_complex', 'electromagnetic_coil'
  ])
  requireParts('mekanismgenerators', advanced, ['fission_reactor/casing', 'fission_reactor/port',
    'fission_reactor/logic_adapter'])
  requireParts('mekanismgenerators', nuclear, [
    'fission_reactor/fuel_assembly', 'fission_reactor/control_rod_assembly', 'reactor/controller'
  ])

  requirePart('create:crafting/kinetics/steam_engine', bronze, [1, 0])
  requireParts('createdieselgenerators', bronze, ['crafting/diesel_engine'])
  event.remove({id: 'createdieselgenerators:crafting/huge_diesel_engine'})
  requireParts('steampowered', bronze, ['furnace_engine'])
  requireParts('steampowered', coil, ['alternator'])
  ;['bronze', 'cast_iron', 'steel'].forEach(metal => event.remove({id: 'steampowered:' + metal + '_steam_engine'}))

  requireParts('createaddition', coil, [
    'mechanical_crafting/alternator', 'mechanical_crafting/electric_motor', 'mechanical_crafting/electric_pump',
    'crafting/modular_accumulator'
  ])
  event.remove({id: 'createaddition:crafting/portable_energy_interface'})
  event.remove({id: 'createaddition:mechanical_crafting/tesla_coil'})

  requireParts('powergrid', coil, [
    'mechanical_crafting/basin_heater', 'mechanical_crafting/electric_motor',
    'mechanical_crafting/generator_commutator', 'mechanical_crafting/generator_induction_rotor',
    'crafting/fe_inverter', 'crafting/hv_breaker'
  ])

  requirePart('createnuclear:mechanical_crafting/reactor_controller', nuclear, [2, 1])
  requirePart('createnuclear:mechanical_crafting/reactor_core', nuclear, [2, 1])
  event.remove({id: 'createnuclear:mixing/steel'})
})
