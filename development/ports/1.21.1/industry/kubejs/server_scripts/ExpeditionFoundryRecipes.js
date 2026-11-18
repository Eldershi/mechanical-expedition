ServerEvents.recipes(event => {
  const path = 'expedition:factory/foundry/'
  const pattern = [{ tag: 'cmi:mechanisms' }, { item: 'create:precision_mechanism' }]
  ;['sand', 'red_sand'].forEach(color => {
    const id = path + 'mechanism_cast_' + color
    event.custom({
      type: 'modernfoundry:molding_table',
      id: id,
      pattern: pattern,
      material: { tag: `modernfoundry:casts/${color}` },
      result: `cmi:mechanism_${color}_cast`
    }).id(id)
  })

  const reusableCasts = [
    ['mechanism_cast', 'c:molten_gold', 90],
    ['bronze_mechanism_cast', 'c:molten_bronze', 360]
  ]
  reusableCasts.forEach(cast => {
    const id = path + cast[0]
    event.custom({
      type: 'modernfoundry:casting_table',
      id: id,
      cast: pattern,
      cast_consumed: true,
      fluid: { tag: cast[1], amount: cast[2] },
      result: { item: `cmi:${cast[0]}` },
      cooling_time: 57
    }).id(id)
  })

  const recycled = [
    ['iron_basement', 'cmi:iron_mechanism_basement', 'modernfoundry:molten_iron', 90, 1535],
    ['copper_basement', 'cmi:copper_mechanism_basement', 'modernfoundry:molten_copper', 90, 1085],
    ['andesite_basement', 'cmi:andesite_mechanism_basement', 'cmi:molten_andesite_alloy', 90, 760],
    ['cast_iron_ingot', 'cmi:cast_iron_ingot', 'cmi:molten_cast_iron', 90, 1200],
    ['cast_iron_dust', 'cmi:cast_iron_dust', 'cmi:molten_cast_iron', 90, 1200],
    ['cast_iron_plate', 'cmi:cast_iron_plate', 'cmi:molten_cast_iron', 90, 1200]
  ]
  recycled.forEach(material => {
    const id = path + 'melting_' + material[0]
    event.custom({
      type: 'modernfoundry:melting',
      id: id,
      ingredient: { item: material[1] },
      result: { fluid: material[2], amount: material[3] },
      temperature: material[4],
      time: 100
    }).id(id)
  })
})
