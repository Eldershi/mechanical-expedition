ServerEvents.recipes(event => {
  const path = 'expedition:factory/engineering/'
  const countedTag = (tag, count) => ({ basePredicate: { tag: tag }, count: count })
  const blueprint = (id, category, inputs, result) => {
    event.custom({
      type: 'immersiveengineering:blueprint',
      category: category,
      inputs: inputs,
      result: result
    }).id(path + 'blueprint/' + id)
  }

  blueprint('component_iron', 'components', [
    countedTag('c:plates/iron', 4), { tag: 'c:gears/copper' }
  ], { id: 'immersiveengineering:component_iron', count: 4 })
  blueprint('component_steel', 'components', [
    countedTag('c:plates/steel', 4), { tag: 'c:gears/electrum' }
  ], { id: 'immersiveengineering:component_steel', count: 4 })
  blueprint('electron_tube', 'components', [
    { tag: 'c:plates/nickel' }, { tag: 'c:wires/copper' }, { item: 'create:polished_rose_quartz' }
  ], { id: 'immersiveengineering:electron_tube', count: 2 })

  const moldForms = ['plate', 'gear', 'rod', 'wire', 'coin', 'bullet', 'mechanism',
    '2x2_packing', '3x3_packing', 'unpack']
  moldForms.forEach(form => {
    const mold = form + '_mold'
    blueprint(mold, 'molds', [countedTag('c:plates/industrial_iron', 4)], { id: 'cmi:' + mold })
  })

  event.shaped('immersiveengineering:blastbrick', ['RR', 'RR'], {
    R: 'immersiveindustry:refractory_kiln_brick'
  }).id(path + 'blastbrick_from_refractory')

  event.custom({
    type: 'immersiveengineering:coke_oven',
    input: { tag: 'c:dusts/wood' },
    result: { id: 'mekanism:dust_charcoal' },
    creosote: 125,
    time: 900
  }).id(path + 'wood_dust_coking')

  const cementColors = ['white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime', 'pink', 'gray',
    'light_gray', 'cyan', 'purple', 'blue', 'brown', 'green', 'red', 'black']
  cementColors.forEach(color => {
    const powder = 'minecraft:' + color + '_concrete_powder'
    event.recipes.create.mixing([
      Fluid.of('createdieselgenerators:' + color + '_cement', 1000),
      CreateItem.of(powder, 0.25)
    ], [powder, Fluid.of('minecraft:water', 100)]).id(path + 'cement/' + color)
  })
})
