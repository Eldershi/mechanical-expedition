// Hide verified duplicate registry IDs, never name-based material guesses.
// event.hide(sourceId) could resolve through OEI and hide the canonical item.
// Use a CustomIngredient predicate over each existing JEI stack instead.
let ExpeditionUnifiedHideIngredient = Java.loadClass('dev.latvian.mods.kubejs.platform.forge.ingredient.CustomIngredient')

JEIEvents.hideItems(event => {
  let config = JSON.parse(String(JsonIO.readJson('kubejs/config/expedition-material-unification.json')))
  let duplicates = new Set()
  let canonicals = new Set()
  config.groups.forEach(group => {
    canonicals.add(group.canonical)
    group.duplicates.forEach(id => duplicates.add(id))
  })
  config.protectedItems.forEach(id => duplicates.delete(id))
  canonicals.forEach(id => duplicates.delete(id))
  let matched = []
  event.getAllIngredients().forEach(stack => {
    let id = String(ForgeRegistries.ITEMS.getKey(stack.getItem()))
    if (duplicates.has(id)) matched.push(id)
  })
  event.hide(new ExpeditionUnifiedHideIngredient(stack => {
    let id = String(ForgeRegistries.ITEMS.getKey(stack.getItem()))
    return duplicates.has(id) && !canonicals.has(id)
  }))
  JsonIO.write('kubejs/exported/expedition-material-jei-audit.json', {
    explicitDuplicateIds: Array.from(duplicates), matchedDuplicateIds: matched,
    canonicalIds: Array.from(canonicals), protectedIds: config.protectedItems,
    selectionMethod: 'actual_jei_stack_registry_id',
    canonicalIdsHidden: matched.filter(id => canonicals.has(id))
  })
  console.info('[Material Unification JEI] explicitDuplicates=' + duplicates.size + ', matched=' + matched.length)
})

// OEI may omit canonical replacement targets from creative-tab ingredients.
// Register actual target stacks after duplicate hiding so recipes remain searchable.
JEIEvents.addItems(event => {
  const config = JSON.parse(String(JsonIO.readJson('kubejs/config/expedition-material-unification.json')))
  const ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
  const ItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
  config.groups.forEach(group => {
    const item = ForgeRegistries.ITEMS.getValue(new ResourceLocation(group.canonical))
    if (item == null) throw new Error('Missing canonical material: ' + group.canonical)
    event.add(new ItemStack(item))
  })
})
