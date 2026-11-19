ServerEvents.recipes(event => {
  const space = 'expedition_space:'
  const desh = '#c:plates/desh'
  const steel = '#c:plates/stainless_steel'
  const optics = 'cmi:optical_fiber'
  const avionics = 'cmi:aeronautic_mechanism'
  const station = (name, parts, energy) => {
    event.custom({
      type: 'neoecoae:integrated_working_station',
      energy: energy || 16000,
      itemOutput: { id: space + name, count: 1 },
      inputItems: parts.map(([id, count]) => id.startsWith('#')
        ? { tag: id.slice(1), count: count } : { item: id, count: count })
    }).id(space + 'station/' + name)
  }
  const frame = space + 'riveted_frame'
  const panel = space + 'structural_panel'
  const glass = space + 'insulated_window'
  event.shaped(Item.of(frame, 8), ['PPP', 'SDS', 'PPP'], {
    P: '#c:plates/copper', S: steel, D: desh
  }).id(space + 'riveted_frame')
  event.shaped(Item.of(panel, 8), ['SSS', 'SMS', 'SSS'], {
    S: 'minecraft:polished_deepslate', M: desh
  }).id(space + 'structural_panel')
  event.shaped(Item.of(glass, 8), ['GGG', 'GRG', 'GGG'], {
    G: 'minecraft:tinted_glass', R: 'cmi:optical_fiber'
  }).id(space + 'insulated_window')
  station('surface_beacon', [[desh, 2], [optics, 2], ['minecraft:redstone_lamp', 1]], 4000)
  station('satellite_relay', [[desh, 4], [frame, 4], [optics, 4], [avionics, 1]])
  station('freight_launchpad', [[desh, 4], [frame, 4], [steel, 4], [avionics, 1]])
  station('space_elevator', [[desh, 4], [panel, 4], ['create:rope_pulley', 1], [avionics, 1]])
  station('orbital_drop_cannon', [[desh, 4], [steel, 4], [glass, 4], [avionics, 1]])
  station('other_gate', [[desh, 8], [frame, 4], [optics, 4], ['minecraft:ender_eye', 2]], 32000)
  station('freight_module', [[desh, 4], [steel, 2], ['minecraft:chest', 1], [avionics, 1]], 8000)
  event.shapeless(space + 'freight_remote', ['minecraft:compass', desh, optics]).id(space + 'freight_remote')
  station('life_support_module', [[desh, 2], ['ad_astra:oxygen_gear', 1],
    ['createcraftedbeginning:airtight_sheet', 2]], 8000)
  station('thermal_lining', [[desh, 2], ['minecraft:netherite_ingot', 1],
    ['createcraftedbeginning:airtight_sheet', 4]], 8000)
})
