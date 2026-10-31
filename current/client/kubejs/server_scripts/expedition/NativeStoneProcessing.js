// priority: -1295
// Apply the user's selected native crushing routes after CMI generation and
// before SelectedParallelRecipes (-1300) captures its retained baseline.
// Leave limestone/lime powder and every non-crushing processing route intact.
let NativeStoneProcessingTypes = Java.loadClass('com.simibubi.create.AllRecipeTypes')
let NativeStoneProcessingHandler = Java.loadClass('net.minecraftforge.items.ItemStackHandler')
let NativeStoneProcessingWrapper = Java.loadClass('net.minecraftforge.items.wrapper.RecipeWrapper')
let NativeStoneProcessingLifecycle = Java.loadClass('net.minecraftforge.server.ServerLifecycleHooks')
let nativeStoneProcessingRemoved = []
let nativeStoneProcessingReport = null
let nativeStoneProcessingAuditPath = 'kubejs/exported/expedition-native-processing-audit.json'

let nativeStoneProcessingTargets = [
  {item: 'create:asurine', tag: 'create:stone_types/asurine', dust: 'cmi:asurine_dust',
    expected: [{item: 'create:crushed_raw_zinc', chance: 0.3}, {item: 'create:zinc_nugget', chance: 0.3}]},
  {item: 'create:crimsite', tag: 'create:stone_types/crimsite', dust: 'cmi:crimsite_dust',
    expected: [{item: 'create:crushed_raw_iron', chance: 0.4}, {item: 'minecraft:iron_nugget', chance: 0.4}]},
  {item: 'create:ochrum', tag: 'create:stone_types/ochrum', dust: 'cmi:ochrum_dust',
    expected: [{item: 'create:crushed_raw_gold', chance: 0.2}, {item: 'minecraft:gold_nugget', chance: 0.2}]},
  {item: 'create:veridium', tag: 'create:stone_types/veridium', dust: 'cmi:veridium_dust',
    expected: [{item: 'create:crushed_raw_copper', chance: 0.8}, {item: 'create:copper_nugget', chance: 0.8}]},
  {item: 'minecraft:netherrack', tag: 'forge:netherrack',
    expected: [{item: 'create:cinder_flour'}, {item: 'create:cinder_flour', chance: 0.5}]},
  {item: 'minecraft:obsidian',
    expected: [{item: 'create:powdered_obsidian'}, {item: 'minecraft:obsidian', chance: 0.75}]},
  {item: 'minecraft:end_stone', tag: 'forge:end_stones', dust: 'cmi:end_stone_dust',
    expected: [{item: 'minecraft:ender_pearl', chance: 0.08}, {item: 'minecraft:end_stone', chance: 0.2}]}
]

function nativeStoneProcessingCanonical(value) {
  if (value == null || typeof value !== 'object') return JSON.stringify(value)
  if (Array.isArray(value)) return '[' + value.map(nativeStoneProcessingCanonical).join(',') + ']'
  return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + nativeStoneProcessingCanonical(value[key])).join(',') + '}'
}

function nativeStoneProcessingNormalizeOutputs(outputs) {
  return outputs.map(output => ({
    item: String(output.item),
    count: output.count == null ? 1 : Number(output.count),
    chance: Math.round((output.chance == null ? 1 : Number(output.chance)) * 1000000) / 1000000
  })).sort((a, b) => nativeStoneProcessingCanonical(a).localeCompare(nativeStoneProcessingCanonical(b)))
}

function nativeStoneProcessingOutputKey(outputs) {
  return nativeStoneProcessingCanonical(nativeStoneProcessingNormalizeOutputs(outputs))
}

function nativeStoneProcessingInputIs(json, input) {
  return nativeStoneProcessingCanonical(json.ingredients) === nativeStoneProcessingCanonical([input])
}

function nativeStoneProcessingRemovalTarget(json) {
  let actual = nativeStoneProcessingOutputKey(json.results || [])
  for (let i = 0; i < nativeStoneProcessingTargets.length; i++) {
    let target = nativeStoneProcessingTargets[i]
    if (!target.dust || target.item === 'minecraft:end_stone') continue
    if (nativeStoneProcessingInputIs(json, {tag: target.tag}) && actual === nativeStoneProcessingOutputKey([
      {item: target.dust, count: 2}, {item: target.dust, chance: 0.5}
    ])) return target.item
  }
  if (nativeStoneProcessingInputIs(json, {tag: 'forge:netherrack'}) && actual === nativeStoneProcessingOutputKey([
    {item: 'minecraft:netherrack'}, {item: 'create:cinder_flour', chance: 0.2}
  ])) return 'minecraft:netherrack'
  if (nativeStoneProcessingInputIs(json, {item: 'minecraft:obsidian'})) {
    // Both aliases are recognized in case material unification runs first.
    // The native recipe has guaranteed powder and only a 75% block return,
    // so it cannot match this exact CMI output signature.
    let aliases = ['mekanism:dust_obsidian', 'create:powdered_obsidian']
    for (let i = 0; i < aliases.length; i++) {
      if (actual === nativeStoneProcessingOutputKey([
        {item: 'minecraft:obsidian'}, {item: aliases[i], chance: 0.5}
      ])) return 'minecraft:obsidian'
    }
  }
  if (nativeStoneProcessingInputIs(json, {tag: 'forge:end_stones'}) && actual === nativeStoneProcessingOutputKey([
    {item: 'cmi:end_stone_dust', count: 4},
    {item: 'cmi:end_stone_dust', count: 3, chance: 0.5},
    {item: 'cmi:end_stone_dust', count: 5, chance: 0.25},
    {item: 'minecraft:end_stone', chance: 0.1}
  ])) return 'minecraft:end_stone'
  return null
}

ServerEvents.recipes(event => {
  nativeStoneProcessingRemoved = []
  function inspect(recipe, origin) {
    if (recipe.removed || String(recipe.getType()) !== 'create:crushing') return
    if (recipe.newRecipe || recipe.hasChanged()) recipe.serialize()
    let json = JSON.parse(String(recipe.json))
    let target = nativeStoneProcessingRemovalTarget(json)
    if (target == null) return
    nativeStoneProcessingRemoved.push({
      target: target, id: String(recipe.getOrCreateId()), origin: origin,
      ingredients: json.ingredients, outputs: nativeStoneProcessingNormalizeOutputs(json.results)
    })
    recipe.remove()
  }
  // This installed KubeJS version's event.remove()/forEachRecipe() omit added
  // recipes. CMI creates these recipes in scripts, so inspect both collections.
  event.originalRecipes.values().forEach(recipe => inspect(recipe, 'originalRecipes'))
  event.addedRecipes.forEach(recipe => inspect(recipe, 'addedRecipes'))
  JsonIO.write('kubejs/exported/expedition-native-processing-removals.json', {
    removed: nativeStoneProcessingRemoved,
    selectedInputs: nativeStoneProcessingTargets.map(target => target.item)
  })
  console.info('[Native Stone Processing] removed CMI crushing conflicts=' + nativeStoneProcessingRemoved.length)
})

function nativeStoneProcessingNativeRecipe(recipe) {
  // In this installed KubeJS version, AfterRecipesLoadedEventJS iterates the
  // native Recipe instances stored in recipeMap (with RecipeKJS mixed in),
  // whereas ServerEvents.recipes uses RecipeJS wrappers. Accept either form
  // explicitly so output inspection never assumes RecipeJS has Create APIs.
  if (typeof recipe.getRollableResults === 'function') return recipe
  if (typeof recipe.getOriginalRecipe === 'function') {
    let original = recipe.getOriginalRecipe()
    if (original != null && typeof original.getRollableResults === 'function') return original
  }
  throw new Error('Expected a native Create ProcessingRecipe for output inspection')
}

function nativeStoneProcessingReadOutputs(recipe) {
  let original = nativeStoneProcessingNativeRecipe(recipe)
  let outputs = []
  let rollable = original.getRollableResults()
  for (let i = 0; i < rollable.size(); i++) {
    let result = rollable.get(i)
    let stack = result.getStack()
    outputs.push({item: String(stack.id), count: stack.getCount(), chance: result.getChance()})
  }
  return nativeStoneProcessingNormalizeOutputs(outputs)
}

function nativeStoneProcessingWriteReport(report) {
  report.passed = report.recipeAuditPassed && report.runtimeSelection.passed === true
  JsonIO.write(nativeStoneProcessingAuditPath, report)
}

function nativeStoneProcessingScheduleRuntimeAudit(server, report) {
  if (server == null || report.runtimeSelection.status === 'scheduled' || report.runtimeSelection.status === 'complete') return
  report.runtimeSelection = {status: 'scheduled', delayTicks: 40, passed: false, rows: []}
  nativeStoneProcessingWriteReport(report)
  server.scheduleInTicks(40, () => {
    // This uses the same Forge RecipeWrapper and RecipeManager.getRecipeFor
    // call that Create's powder-wheel controller uses, without placing blocks
    // or consuming player items. The recipe audit above also checks every
    // matching candidate, so identical native base/recycling duplicates are safe.
    try {
      let level = server.overworld()
      let manager = server.getRecipeManager()
      let rows = []
      nativeStoneProcessingTargets.forEach(target => {
        let handler = new NativeStoneProcessingHandler(1)
        handler.setStackInSlot(0, Item.of(target.item))
        let wrapper = new NativeStoneProcessingWrapper(handler)
        let found = manager.getRecipeFor(NativeStoneProcessingTypes.CRUSHING.getType(), wrapper, level)
        let row = {input: target.item, present: found.isPresent(), id: null, outputs: [], passed: false}
        if (found.isPresent()) {
          let recipe = found.get()
          row.id = String(recipe.getId())
          row.outputs = nativeStoneProcessingReadOutputs(recipe)
          row.passed = nativeStoneProcessingOutputKey(row.outputs) === nativeStoneProcessingOutputKey(target.expected)
        }
        rows.push(row)
      })
      report.runtimeSelection = {
        status: 'complete', method: 'RecipeManager.getRecipeFor(create:crushing, RecipeWrapper, overworld)',
        delayTicks: 40, rows: rows, passed: rows.every(row => row.passed)
      }
    } catch (error) {
      report.runtimeSelection = {status: 'error', passed: false, error: String(error), rows: []}
      console.error('[Native Stone Processing] runtime selection audit failed: ' + error)
    }
    nativeStoneProcessingWriteReport(report)
    console.info('[Native Stone Processing] runtime selection audit passed=' + report.passed)
  })
}

ServerEvents.afterRecipes(event => {
  let rows = nativeStoneProcessingTargets.map(target => ({
    input: target.item, expected: nativeStoneProcessingNormalizeOutputs(target.expected),
    candidates: [], passed: false,
    removedCmiCount: nativeStoneProcessingRemoved.filter(row => row.target === target.item).length
  }))
  event.forEachRecipe({type: 'create:crushing'}, recipe => {
    let original = nativeStoneProcessingNativeRecipe(recipe)
    let ingredients = original.getIngredients()
    if (ingredients.size() !== 1) return
    for (let i = 0; i < rows.length; i++) {
      if (!ingredients.get(0).test(Item.of(rows[i].input))) continue
      let outputs = nativeStoneProcessingReadOutputs(recipe)
      rows[i].candidates.push({id: String(recipe.getOrCreateId()), outputs: outputs,
        matchesNative: nativeStoneProcessingOutputKey(outputs) === nativeStoneProcessingOutputKey(rows[i].expected)})
    }
  })
  rows.forEach(row => {
    row.passed = row.removedCmiCount === 1 && row.candidates.length > 0 && row.candidates.every(candidate => candidate.matchesNative)
  })
  nativeStoneProcessingReport = {
    scope: 'Seven requested native crushing routes; limestone/lime powder and non-crushing routes preserved',
    removed: nativeStoneProcessingRemoved, inputs: rows,
    recipeAuditPassed: rows.every(row => row.passed),
    runtimeSelection: {status: 'waiting_for_server', passed: false, rows: []}, passed: false
  }
  nativeStoneProcessingWriteReport(nativeStoneProcessingReport)
  if (!nativeStoneProcessingReport.recipeAuditPassed) {
    throw new Error('Native crushing candidate audit failed: ' + JSON.stringify(rows))
  }
  nativeStoneProcessingScheduleRuntimeAudit(NativeStoneProcessingLifecycle.getCurrentServer(), nativeStoneProcessingReport)
})

// Startup can prepare recipes before server worlds exist. A 40-tick scheduled
// audit from loaded covers that lifecycle, while afterRecipes covers /reload.
ServerEvents.loaded(event => {
  if (nativeStoneProcessingReport != null) nativeStoneProcessingScheduleRuntimeAudit(event.server, nativeStoneProcessingReport)
})
