ServerEvents.recipes(event => {
  const path = 'expedition:factory/airtight_equipment/'
  const airtight = 'cmi:air_tight_mechanism'

  event.stonecutting('cmi:air_tight_machine', airtight).id(path + 'air_tight_machine')

  event.shaped('mekanism:basic_chemical_tank', ['A', 'M', 'A'], {
    A: '#c:plates/stainless_steel',
    M: airtight
  }).id(path + 'basic_chemical_tank')

  event.shaped('2x appmek:chemical_cell_housing', ['PAP', 'AMA', 'PAP'], {
    P: '#c:plates/osmium',
    A: 'ae2:quartz_glass',
    M: airtight
  }).id(path + 'chemical_cell_housing')

  const advanced = 'cmi:advanced_mekanism_mechanism'
  const elite = 'cmi:elite_mekanism_mechanism'
  const tungsten = 'c:plates/composite_tungsten_steel'
  const carbon = 'c:plates/composite_carbon_fiber'
  const chemicalTank = 'mekanism:basic_chemical_tank'
  const fluidTank = 'mekanism:basic_fluid_tank'
  const enrichmentChamber = 'mekanism:enrichment_chamber'
  const whisk = 'create:whisk'
  const input = (item, count) => ({item: item, count: count || 1})

  const machines = [
    ['osmium_compressor', advanced, tungsten, [input(fluidTank)]],
    ['purification_chamber', advanced, tungsten, [input(enrichmentChamber)]],
    ['chemical_oxidizer', advanced, tungsten, [input('minecraft:blaze_rod')]],
    ['chemical_injection_chamber', advanced, tungsten, [
      input('cmi:chromeplated_steel_gear', 2), input('mekanism:purification_chamber')
    ]],
    ['chemical_infuser', advanced, tungsten, [input(chemicalTank)]],
    ['isotopic_centrifuge', advanced, tungsten, [
      input('cmi:nuclear_mechanism'), {tag: 'c:ingots/lead', count: 1}
    ]],
    ['chemical_dissolution_chamber', elite, carbon, [input(whisk), input(chemicalTank)]],
    ['chemical_washer', elite, carbon, [input(whisk), input(fluidTank)]],
    ['chemical_crystallizer', elite, carbon, [input(whisk), {tag: 'c:gems/fluorite', count: 1}]],
    ['solar_neutron_activator', elite, carbon, [
      input('ad_astra:photovoltaic_vesnium_cell'), input('mekanism:hdpe_sheet')
    ]],
    ['pressurized_reaction_chamber', elite, carbon, [
      input('vintageimprovements:vacuum_chamber'), input(enrichmentChamber)
    ]]
  ]

  machines.forEach(([name, mechanism, plate, parts]) => {
    event.custom({
      type: 'neoecoae:integrated_working_station',
      energy: 2000,
      itemOutput: {id: 'mekanism:' + name, count: 1},
      inputFluid: {fluid: 'cmi:silicon_rubber', amount: 200},
      inputItems: [
        input('mekanism:steel_casing'),
        {tag: plate, count: 2},
        input(mechanism),
        input(airtight)
      ].concat(parts)
    }).id(path + name)
  })
})
