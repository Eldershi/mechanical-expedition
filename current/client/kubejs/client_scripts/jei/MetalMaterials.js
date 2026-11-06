// Select material duplicates by registered ID before OEI ingredient conversion.
const ExpeditionMetalHideIngredient = Java.loadClass('dev.latvian.mods.kubejs.platform.forge.ingredient.CustomIngredient')

JEIEvents.hideItems(event => {
  const priorities = ['cmi', 'vintageimprovements', 'thermal', 'thermalconstruct',
    'thermalendergy', 'thermal_extra', 'create', 'createdeco', 'ae2', 'ad_astra',
    'createaddition', 'immersiveengineering', 'mekanism', 'alexscaves', 'tconstruct', 'minecraft']
  const config = JSON.parse(String(JsonIO.readJson('kubejs/config/expedition-material-unification.json')))
  const canonicalIds = new Set(config.groups.map(group => group.canonical))
  const protectedIds = new Set(config.protectedItems)
  const registered = new Set()
  ForgeRegistries.ITEMS.getKeys().toArray().forEach(key => registered.add(String(key)))
  const hidden = new Set()

  function paths(type, material) {
    if (type === 'ingot') return [material + '_ingot', 'ingot_' + material, material]
    if (type === 'plate') return [material + '_plate', 'plate_' + material, material + '_sheet', 'sheet_' + material]
    if (type === 'storage_block') return [material + '_block', 'block_' + material, 'block_of_' + material, 'storage_' + material]
    if (type === 'raw_material') return ['raw_' + material, material + '_raw']
    if (type === 'raw_storage_block') return ['raw_' + material + '_block', material + '_raw_block', 'raw_block_' + material, 'block_raw_' + material, 'block_of_raw_' + material]
    return [material + '_' + type, type + '_' + material]
  }

  CmiMetal.getAll().forEach(metal => {
    const material = String(metal.getId())
    ;['ingot', 'plate', 'nugget', 'storage_block', 'gear', 'dust', 'rod', 'wire',
      'raw_material', 'raw_storage_block'].forEach(type => {
      const candidates = []
      priorities.forEach(namespace => paths(type, material).forEach(path => {
        const id = namespace + ':' + path
        if (registered.has(id) && candidates.indexOf(id) < 0) candidates.push(id)
      }))
      const canonical = candidates.find(id => canonicalIds.has(id)) || candidates[0]
      candidates.forEach(id => {
        if (id !== canonical && !canonicalIds.has(id) && !protectedIds.has(id)) hidden.add(id)
      })
    })
  })

  event.hide(new ExpeditionMetalHideIngredient(stack => {
    const id = String(ForgeRegistries.ITEMS.getKey(stack.getItem()))
    return hidden.has(id) && !canonicalIds.has(id) && !protectedIds.has(id)
  }))
  JsonIO.write('kubejs/exported/expedition-metal-jei-selection.json', {
    hiddenIds: Array.from(hidden), canonicalIds: Array.from(canonicalIds),
    canonicalIdsHidden: Array.from(hidden).filter(id => canonicalIds.has(id))
  })
})
