StartupEvents.registry('block', event => {
  event.create('cmi:galena_titanium_ore')
    .displayName('Galena Titanium Ore')
    .defaultCutout()
    .color(0, 0xE2B1E3)
    .item(item => item.color(0, 0xE2B1E3))
    .parentModel('nebula_libs:block/ore/simple_double_layered')
    .textures({background: 'alexscaves:block/galena', ore: 'cmi:block/ore/assets/ore_8', particle: 'alexscaves:block/galena'})
    .soundType(SoundType.STONE)
    .hardness(20).resistance(20).requiresTool()
    .tagBlock('minecraft:mineable/pickaxe')
    .tagBlock('minecraft:needs_diamond_tool')
    .tagBoth('cmi:ores').tagBoth('c:ores').tagBoth('c:ores/titanium')
})

StartupEvents.registry('item', event => {
  const metals = {
    titanium_ingot: ['Titanium Ingot', 'ingot', 0xB9C8D2, 'c:ingots/titanium'],
    titanium_plate: ['Titanium Plate', 'plate', 0xB9C8D2, 'c:plates/titanium'],
    titanium_alloy_ingot: ['Titanium Alloy Ingot', 'ingot', 0x9EB3C5, 'c:ingots/titanium_alloy'],
    titanium_alloy_plate: ['Titanium Alloy Plate', 'plate', 0x9EB3C5, 'c:plates/titanium_alloy'],
    tungsten_plate: ['Tungsten Plate', 'plate', 0x686775, 'c:plates/tungsten'],
    tungsten_steel_plate: ['Tungsten Steel Plate', 'plate', 0x626E81, 'c:plates/tungsten_steel'],
    superconducting_mercury_ingot: ['Superconducting Mercury Ingot', 'ingot', 0x91CDE3, 'c:ingots/superconducting_mercury'],
    superconducting_mercury_plate: ['Superconducting Mercury Plate', 'plate', 0x91CDE3, 'c:plates/superconducting_mercury'],
    etrium_dust: ['Etrium Dust', 'dust', 0x32FFD4, 'c:dusts/etrium']
  }
  Object.keys(metals).forEach(name => {
    const [label, shape, color, tag] = metals[name]
    event.create('cmi:' + name)
      .displayName(label)
      .texture('cmi:item/material/color/' + shape + '/' + shape)
      .color(0, color)
      .tag(tag)
  })
  for (const [name, label, color] of [
    ['tungsten_steel', 'Tungsten Steel', 0x626E81], ['desh', 'Desh', 0xB27752],
    ['ostrum', 'Ostrum', 0x8E718B], ['calorite', 'Calorite', 0xBC674F]
  ]) {
    event.create('cmi:' + name + '_gear')
      .displayName(label + ' Gear')
      .texture('cmi:item/material/color/gear/gear')
      .color(0, color)
      .tag('c:gears/' + name)
  }
  for (let tier = 1; tier <= 4; tier++) {
    for (const [part, label] of [['nose_cone', 'Nose Cone'], ['body', 'Body'], ['fin', 'Fin']]) {
      event.create(`cmi:tier_${tier}_rocket_${part}`)
        .displayName(`Tier ${tier} Rocket ${label}`)
        .texture(`cmi:item/material/rocket_${part}/${tier}`)
    }
  }
})

StartupEvents.registry('mekanism:chemical', event => {
  for (const [id, color] of [
    ['mercury_mixture', 0xD2A9FF], ['overheated_mercury_mixture', 0xD2A9FF],
    ['titanium_oxide', 0x60459E], ['radon', 0x00FF00]
  ]) event.create('cmi:' + id).tint(color).gaseous()
})
StartupEvents.registry('fluid', event => {
  for (const [id, label, tint] of [
    ['polymeric_carbon_solution', 'Polymeric Carbon Solution', 0x3F454E],
    ['ferrouslime', 'Ferrouslime', 0x7D6257],
    ['composite_magnetic_fluid', 'Composite Magnetic Fluid', 0x796A8D]
  ]) {
    event.create('cmi:' + id).displayName(label)
      .stillTexture('minecraft:block/water_still').flowingTexture('minecraft:block/water_flow')
      .tint(tint).tag('cmi:' + id)
  }
})
