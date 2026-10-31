// priority: -1300
// Add selected native routes after all CMI replacements. Existing IDs stay intact.
let SelectedNativeSchema = Java.loadClass('dev.latvian.mods.kubejs.recipe.schema.JsonRecipeSchema')
let SelectedNativeLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
let SelectedForgeHelper = new (Java.loadClass('dev.latvian.mods.kubejs.platform.forge.RecipeForgeHelper'))()
// CMI items implement JavaScript callbacks (e.g. isDamageable). Calling them
// from KubeJS recipe worker threads causes Rhino assertions and missing recipes.
// Disable asynchronous script lookups; warm native recipes on this thread below.
// In-world machine processing is unchanged.
Java.loadClass('dev.latvian.mods.kubejs.CommonProperties').get().allowAsyncStreams = false
let selectedParallelState = null

function selectedRecipeCanonical(node) {
  if (node == null || typeof node !== 'object') return JSON.stringify(node)
  if (Array.isArray(node)) return '[' + node.map(selectedRecipeCanonical).join(',') + ']'
  return '{' + Object.keys(node).sort().map(key => JSON.stringify(key) + ':' + selectedRecipeCanonical(node[key])).join(',') + '}'
}

// KubeJS forEachRecipe omits addedRecipes. Merge the effective map so an
// added CMI recipe with an existing ID takes precedence over the original.
function selectedEffectiveRecipes(event, consumer) {
  let effective = {}
  event.originalRecipes.values().forEach(recipe => {
    if (!recipe.removed) effective[String(recipe.getOrCreateId())] = recipe
  })
  event.addedRecipes.forEach(recipe => {
    if (recipe.newRecipe && !recipe.removed) effective[String(recipe.getOrCreateId())] = recipe
  })
  Object.keys(effective).forEach(id => consumer(effective[id]))
}

function selectedCurrentJson(recipe) {
  if (recipe.newRecipe || recipe.hasChanged()) recipe.serialize()
  let json = JSON.parse(String(recipe.json))
  // KubeJS assigns the schema serializer only during createRecipe().
  if (recipe.newRecipe) json.type = String(recipe.getType())
  return selectedRecipeCanonical(json)
}

// Official Lethality 0.4.1 ships this shaped recipe with undefined symbol W.
// Only an unchanged native recipe with the complete frozen JSON is classified.
// Same-ID repairs/replacements remain part of the strict retained baseline.
// Source jar SHA256: 38d8cfe4ddaf798efa1a1ec5ae4cd0281a2afbec42a59f6009070cfa76bc8584
let selectedMalformedNativeId = 'lethality:broken_biome_blade'
let selectedMalformedNativeCanonical = selectedRecipeCanonical({"type":"minecraft:crafting_shaped","pattern":["184","5W7","263"],"key":{"1":{"item":"terramity:topaz_sword"},"2":{"item":"terramity:ruby_sword"},"3":{"item":"terramity:sapphire_sword"},"4":{"item":"terramity:onyx_sword"},"5":{"item":"terramity:sapphire"},"6":{"item":"terramity:ruby"},"7":{"item":"terramity:topaz"},"8":{"item":"terramity:onyx"},"A":{"item":"minecraft:barrier"}},"result":{"item":"lethality:broken_biome_blade","count":1}})

function selectedIsKnownMalformedNative(recipe, id, canonical) {
  return id === selectedMalformedNativeId && !recipe.newRecipe && !recipe.hasChanged() &&
    canonical === selectedMalformedNativeCanonical
}

ServerEvents.recipes(event => {
  let catalog = JsonIO.readJson('kubejs/config/expedition-selected-native-recipes.json').getAsJsonObject()
  let state = {selected: catalog.get('selectionCount').getAsInt(), retained: {}, rows: [],
    labels: {modified: [], native: []}, changedExisting: [], failed: [], serializationRepairs: [], knownMalformedNative: []}
  let byId = {}
  let byJson = {}
  let knownUnavailable = {}
  if (catalog.has('baselineUnavailable')) catalog.getAsJsonArray('baselineUnavailable').forEach(value => {
    knownUnavailable[String(value.getAsString())] = true
  })
  event.forEachRecipe({type: 'farmersdelight:cutting'}, recipe => {
    if (!recipe.newRecipe && !recipe.hasChanged()) recipe.getOriginalRecipe()
  })
  selectedEffectiveRecipes(event, recipe => {
    let id = String(recipe.getOrCreateId())
    let json = selectedCurrentJson(recipe)
    byId[id] = recipe
    if (selectedIsKnownMalformedNative(recipe, id, json)) {
      state.knownMalformedNative.push({id: id, reason: 'native_shaped_pattern_undefined_W', canonicalJson: json})
      console.warn('[Selected Parallel] known malformed native recipe excluded from valid-retention baseline: ' + id + ' (undefined pattern symbol W)')
      return
    }
    if (!knownUnavailable[id] && (recipe.newRecipe || !recipe.hasChanged())) byJson[json] = id
    state.retained[id] = json
    if (id.startsWith('expedition:pre_steam/') || id === 'expedition:mixing/brass_ingot') {
      state.labels.native.push(id)
    } else if (recipe.newRecipe || recipe.hasChanged()) {
      state.labels.modified.push(id)
    }
  })
  JsonIO.write('kubejs/exported/baseline-json.json', state.retained)
  state.knownUnavailable = knownUnavailable
  catalog.getAsJsonArray('recipes').forEach(entry => {
    let row = entry.getAsJsonObject()
    let id = String(row.get('id').getAsString())
    let nativeId = String(row.get('nativeId').getAsString())
    let json = SelectedForgeHelper.checkConditions(row.getAsJsonObject('json'))
    if (json == null) {
      state.rows.push({nativeId: nativeId, status: 'native_condition_disabled'})
      return
    }
    let canonical = selectedRecipeCanonical(JSON.parse(String(json)))
    let equalId = byJson[canonical]
    if (equalId != null) {
      state.rows.push({nativeId: nativeId, id: equalId, status: 'already_available'})
      return
    }
    if (Object.prototype.hasOwnProperty.call(byId, id)) throw new Error('Native recipe ID collision: ' + id)
    try {
      let recipe = SelectedNativeSchema.SCHEMA.deserialize(
        event.getRecipeFunction(json.get('type').getAsString()), new SelectedNativeLocation(id), json.deepCopy())
      // JsonRecipeSchema has no value holders; cache exactly this native JSON
      // before KubeJS later submits the collection to its hard-coded worker pool.
      recipe.originalJson = json.deepCopy()
      recipe.newRecipe = false
      recipe.changed = false
      if (recipe.getOriginalRecipe() == null) throw new Error('Native serializer returned no recipe')
      // The installed KubeJS removes addedRecipes entries with newRecipe=false.
      // Its public originalRecipes map accepts a pre-parsed, unchanged recipe;
      // our reserved namespace and collision check prevent replacing any entry.
      event.originalRecipes.put(new SelectedNativeLocation(id), recipe)
      byJson[canonical] = id
      state.labels.native.push(id)
      state.rows.push({nativeId: nativeId, id: id, status: 'added', type: String(json.get('type').getAsString())})
    } catch (error) {
      state.failed.push({id: id, error: String(error)})
      console.error('[Selected Parallel] Failed ' + id + ': ' + error)
    }
  })
  selectedEffectiveRecipes(event, recipe => {
    let id = String(recipe.getOrCreateId())
    if (Object.prototype.hasOwnProperty.call(state.retained, id)) {
      let canonical = selectedCurrentJson(recipe)
      if (canonical !== state.retained[id]) state.changedExisting.push(id)
    }
  })
  selectedParallelState = state
  JsonIO.write('kubejs/exported/expedition-recipe-labels.json', state.labels)
  JsonIO.write('kubejs/exported/expedition-parallel-preflight.json', {
    retainedIds: Object.keys(state.retained), changedExisting: state.changedExisting, failed: state.failed, rows: state.rows, knownMalformedNative: state.knownMalformedNative})
  console.info('[Selected Parallel] prepared=' + state.rows.length + ', existingChanged=' + state.changedExisting.length + ', failed=' + state.failed.length + ', knownMalformedNative=' + state.knownMalformedNative.length)
})

ServerEvents.afterRecipes(event => {
  if (selectedParallelState == null) return
  let state = selectedParallelState
  let present = {}
  let emptyInputs = []
  let inactiveOptionalVariants = []
  event.forEachRecipe({}, recipe => {
    let id = String(recipe.getOrCreateId())
    present[id] = true
    if (!id.startsWith('expedition:selected_native/')) return
    let ingredients = recipe.getIngredients()
    for (let i = 0; i < ingredients.size(); i++) {
      let ingredient = ingredients.get(i)
      let ingredientJson = String(ingredient.toJson())
      if (ingredient.getItemIds().isEmpty() && ingredientJson !== '[]' && ingredientJson !== '{}') {
        let detail = {id: id, slot: i, ingredient: ingredientJson}
        if ((id.endsWith('/ore_dense') || id.endsWith('/ore_sparse') || id.endsWith('/cluster')) &&
          (ingredientJson.indexOf('forge:intersection') >= 0 || ingredientJson === '{"item":"minecraft:air"}')) inactiveOptionalVariants.push(detail)
        else emptyInputs.push(detail)
      }
    }
  })
  let excludedInvalidNative = state.knownMalformedNative.filter(row => !present[row.id])
  let baselineUnavailable = Object.keys(state.retained).filter(id => !present[id] && state.knownUnavailable[id])
  let missingRetained = Object.keys(state.retained).filter(id => !present[id] && !state.knownUnavailable[id])
  let missingNative = state.rows.filter(row => row.id != null && !present[row.id])
  let counts = {added: 0, already_available: 0, native_condition_disabled: 0}
  state.rows.forEach(row => counts[row.status]++)
  let report = {selectedItems: state.selected, counts: counts, retainedCount: Object.keys(state.retained).length,
    missingRetained: missingRetained, missingNative: missingNative, changedExisting: state.changedExisting,
    emptyInputs: emptyInputs, inactiveOptionalVariants: inactiveOptionalVariants, failed: state.failed, baselineUnavailable: baselineUnavailable,
    knownMalformedNative: state.knownMalformedNative, excludedInvalidNative: excludedInvalidNative,
    passed: missingRetained.length === 0 && missingNative.length === 0 && state.changedExisting.length === 0 && state.failed.length === 0 && emptyInputs.length === 0}
  JsonIO.write('kubejs/exported/expedition-selected-parallel-audit.json', report)
  console.info('[Selected Parallel] passed=' + report.passed + ', added=' + counts.added + ', existing=' + counts.already_available + ', emptyInputs=' + emptyInputs.length + ', excludedInvalidNative=' + excludedInvalidNative.length)
  if (!report.passed) throw new Error('Selected parallel recipe audit failed: ' + JSON.stringify(report))
})
