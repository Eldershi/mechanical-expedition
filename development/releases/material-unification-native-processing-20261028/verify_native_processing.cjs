// Source-backed offline contract checks. This is not a Forge runtime test.
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const assert = require('node:assert/strict')
const release = __dirname
const source = fs.readFileSync(path.join(release, 'payload/kubejs/server_scripts/expedition/NativeStoneProcessing.js'), 'utf8')
const fixture = JSON.parse(fs.readFileSync(path.join(release, 'evidence/native-processing-source-fixture.json'), 'utf8'))
const rawForTag = {
  'create:stone_types/asurine': 'create:asurine',
  'create:stone_types/crimsite': 'create:crimsite',
  'create:stone_types/ochrum': 'create:ochrum',
  'create:stone_types/veridium': 'create:veridium',
  'create:stone_types/limestone': 'create:limestone',
  'forge:netherrack': 'minecraft:netherrack',
  'forge:end_stones': 'minecraft:end_stone'
}
function ingredientMatches(ingredient, stack) {
  if (Array.isArray(ingredient)) return ingredient.some(child => ingredientMatches(child, stack))
  return ingredient.item === stack.id || rawForTag[ingredient.tag] === stack.id
}
function list(values) { return {size: () => values.length, get: i => values[i]} }
function recipe(row, isNew = false) {
  const json = JSON.parse(JSON.stringify(row.json))
  const native = {
    id: row.id, data: json,
    getOrCreateId: () => row.id, getId: () => row.id,
    getIngredients: () => list(json.ingredients.map(input => ({test: stack => ingredientMatches(input, stack)}))),
    getRollableResults: () => list(json.results.map(output => ({
      getStack: () => ({id: output.item, getCount: () => output.count == null ? 1 : output.count}),
      getChance: () => Math.fround(output.chance == null ? 1 : output.chance)
    })))
  }
  // RecipesEventJS exposes RecipeJS wrappers; its afterRecipes counterpart
  // instead iterates native Recipe values from its final recipeMap. Keep those
  // interfaces separate, as verified from the installed KubeJS bytecode.
  return {
    id: row.id, data: json, json: JSON.stringify(json), removed: false, newRecipe: isNew,
    hasChanged: () => false, serialize() { this.json = JSON.stringify(this.data) },
    getType: () => json.type, getOrCreateId: () => row.id, getId: () => row.id,
    remove() { this.removed = true },
    getOriginalRecipe: () => native
  }
}
function run({mixedCollections = false, unexpectedConflict = false, staleRuntime = false} = {}) {
  const cmi = fixture.cmi.map((row, i) => recipe(row, !mixedCollections || i >= 3))
  const preserved = fixture.preserved.map(row => recipe(row, true))
  const native = fixture.native.map(row => recipe(row))
  const originals = mixedCollections ? cmi.slice(0, 3) : []
  const added = [...cmi.filter(r => r.newRecipe), ...preserved]
  if (unexpectedConflict) added.push(recipe({id: 'test:unexpected_crimsite_variant', json: {
    type: 'create:crushing', ingredients: [{item: 'create:crimsite'}],
    results: [{item: 'minecraft:diamond'}]
  }}, true))
  const events = {}, writes = {}, scheduled = []
  const current = () => [...originals, ...added, ...native].filter(r => !r.removed)
  const manager = {getRecipeFor(type, wrapper) {
    let found = current().find(r => r.data.type === type && r.data.ingredients.length === 1 && ingredientMatches(r.data.ingredients[0], wrapper.handler.stack))
    if (staleRuntime && wrapper.handler.stack.id === 'minecraft:obsidian') found = cmi.find(r => r.data.ingredients[0].item === 'minecraft:obsidian')
    return {isPresent: () => !!found, get: () => found.getOriginalRecipe()}
  }}
  const server = {scheduleInTicks(delay, task) { assert.equal(delay, 40); scheduled.push(task) }, overworld: () => ({}), getRecipeManager: () => manager}
  class Handler { constructor(size) { assert.equal(size, 1) } setStackInSlot(slot, stack) { assert.equal(slot, 0); this.stack = stack } }
  class Wrapper { constructor(handler) { this.handler = handler } }
  const classes = {
    'com.simibubi.create.AllRecipeTypes': {CRUSHING: {getType: () => 'create:crushing'}},
    'net.minecraftforge.items.ItemStackHandler': Handler,
    'net.minecraftforge.items.wrapper.RecipeWrapper': Wrapper,
    'net.minecraftforge.server.ServerLifecycleHooks': {getCurrentServer: () => server}
  }
  const context = vm.createContext({
    Java: {loadClass(name) { assert.ok(classes[name], name); return classes[name] }},
    ServerEvents: Object.fromEntries(['recipes', 'afterRecipes', 'loaded'].map(name => [name, callback => { events[name] = callback }])),
    Item: {of: id => ({id})},
    JsonIO: {write(name, data) { writes[name] = JSON.parse(JSON.stringify(data)) }},
    console: {info() {}, error() {}}
  })
  vm.runInContext(source, context, {filename: 'NativeStoneProcessing.js'})
  events.recipes({originalRecipes: {values: () => originals}, addedRecipes: added})
  assert.equal(cmi.filter(r => r.removed).length, 7, 'all seven source CMI signatures must be removed')
  assert.ok(preserved.every(r => !r.removed), 'lime crushing and end-stone milling remain')
  assert.ok(native.every(r => !r.removed), 'native outputs must not match CMI removal signatures')
  let failure = null
  try { events.afterRecipes({forEachRecipe(filter, consumer) { current().filter(r => r.data.type === filter.type).forEach(r => consumer(r.getOriginalRecipe())) }}) }
  catch (error) { failure = error }
  if (unexpectedConflict) {
    assert.match(String(failure), /candidate audit failed/)
    assert.equal(writes['kubejs/exported/expedition-native-processing-audit.json'].recipeAuditPassed, false)
  } else {
    assert.equal(failure, null)
    assert.equal(scheduled.length, 1)
    scheduled.shift()()
    const report = writes['kubejs/exported/expedition-native-processing-audit.json']
    assert.equal(report.recipeAuditPassed, true)
    assert.equal(report.runtimeSelection.rows.length, 7)
    assert.equal(report.passed, !staleRuntime)
    assert.equal(report.runtimeSelection.rows.filter(row => !row.passed).length, staleRuntime ? 1 : 0)
  }
}
run()
run({mixedCollections: true})
run({unexpectedConflict: true})
run({staleRuntime: true})
const report = {
  passed: true,
  sourceFixture: '7 historical CMI recipe JSONs, 11 unchanged Create/UF native JSONs, 2 preservation cases',
  checks: [
    'removes script-added CMI conflicts',
    'handles CMI conflicts split across originalRecipes and addedRecipes',
    'preserves limestone crushing, end-stone milling and all native candidates',
    'handles native raw-stone/recycling duplicates with equivalent output distributions',
    'normalizes Java float probabilities',
    'models RecipeJS and native ProcessingRecipe as separate interfaces',
    'fails candidate audit on an additional same-input/different-output recipe',
    'fails runtime audit if the recipe manager returns a stale CMI choice'
  ],
  limitation: 'Offline source-backed stubs verify script behavior; actual Forge audit is performed on the target server after installation.'
}
fs.writeFileSync(path.join(release, 'evidence/native-processing-offline-verification.json'), JSON.stringify(report, null, 2) + '\n')
console.log(JSON.stringify(report, null, 2))
