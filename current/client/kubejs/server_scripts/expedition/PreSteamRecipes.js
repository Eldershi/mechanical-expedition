// priority: -1000
// 两套配方并行：只增加原模组配方，保留 CMI 物品及全部原有配方。
// 原配方 JSON 提取自当前安装 JAR；独立 ID 避免与上游同 ID 魔改冲突。
const ExpeditionNativeCraftingHelper = Java.loadClass('net.minecraftforge.common.crafting.CraftingHelper')
const ExpeditionNativeConditionContext = Java.loadClass('net.minecraftforge.common.crafting.conditions.ICondition$IContext')
const ExpeditionNativeJsonSchema = Java.loadClass('dev.latvian.mods.kubejs.recipe.schema.JsonRecipeSchema')
const ExpeditionNativeResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')

function expeditionSelectNativeRecipe(json) {
  if (!ExpeditionNativeCraftingHelper.processConditions(json, 'conditions', ExpeditionNativeConditionContext.EMPTY)) return null
  if (String(json.get('type').getAsString()) !== 'forge:conditional') return json
  let branches = json.getAsJsonArray('recipes')
  for (let i = 0; i < branches.size(); i++) {
    let branch = branches.get(i).getAsJsonObject()
    if (ExpeditionNativeCraftingHelper.processConditions(branch, 'conditions', ExpeditionNativeConditionContext.EMPTY)) {
      return expeditionSelectNativeRecipe(branch.getAsJsonObject('recipe'))
    }
  }
  return null
}

ServerEvents.recipes(event => {
  let catalog = JsonIO.readJson('kubejs/config/expedition-pre-steam-recipes.json').getAsJsonObject()
  let entries = catalog.getAsJsonArray('recipes')
  let added = 0
  let skipped = 0
  entries.forEach(entry => {
    let row = entry.getAsJsonObject()
    try {
      let json = expeditionSelectNativeRecipe(row.getAsJsonObject('json'))
      if (json == null) {
        skipped++
      } else {
        // Use KubeJS's native-JSON fallback: some installed TConstruct schemas
        // cannot read valid native fluid-tag JSON. Keep the mod serializer and
        // original JSON rather than converting through those builder schemas.
        let recipe = ExpeditionNativeJsonSchema.SCHEMA.deserialize(
          event.getRecipeFunction(json.get('type').getAsString()),
          new ExpeditionNativeResourceLocation(row.get('id').getAsString()), json.deepCopy())
        recipe.newRecipe = true
        event.addRecipe(recipe, true)
        added++
      }
    } catch (error) {
      console.error(`[Expedition Pre-Steam] Could not add ${row.get('nativeId').getAsString()}: ${error}`)
      throw error
    }
  })
  console.info(`[Expedition Pre-Steam] added=${added}, disabledByNativeConditions=${skipped}; existing CMI recipes retained`)
})

ServerEvents.loaded(event => {
  let catalog = JsonIO.readJson('kubejs/config/expedition-pre-steam-recipes.json').getAsJsonObject()
  let manager = event.server.getRecipeManager()
  let registry = event.server.registryAccess()
  let ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
  let missing = []
  let wrongOutput = []
  let enabled = 0
  let skipped = 0
  catalog.getAsJsonArray('recipes').forEach(entry => {
    let row = entry.getAsJsonObject()
    let json = expeditionSelectNativeRecipe(row.getAsJsonObject('json'))
    if (json == null) {
      skipped++
      return
    }
    enabled++
    let id = String(row.get('id').getAsString())
    let recipe = manager.byKey(new ResourceLocation(id))
    if (!recipe.isPresent()) {
      missing.push(id)
      return
    }
    let output = String(recipe.get().getResultItem(registry).id)
    let expected = json.has('result') ? json.get('result') : json.getAsJsonArray('results').get(0)
    let expectedId = expected.isJsonPrimitive() ? String(expected.getAsString()) : String(expected.getAsJsonObject().get('item').getAsString())
    if (output !== expectedId) wrongOutput.push({id: id, expected: expectedId, actual: output})
  })
  let retainedIds = ['minecraft:furnace', 'create:crafting/kinetics/water_wheel',
    'create:crafting/kinetics/mechanical_press', 'create:crafting/kinetics/spout',
    'create:crafting/kinetics/steam_engine', 'create:crafting/kinetics/mechanical_crafter']
  let missingRetained = retainedIds.filter(id => !manager.byKey(new ResourceLocation(id)).isPresent())
  let constructCounts = {}
  ;['wooden', 'stone', 'andesite', 'copper', 'iron', 'bronze'].forEach(name => {
    constructCounts[`cmi:${name}_mechanism`] = 0
  })
  let RecipeMap = Java.loadClass('java.util.Map')
  function countConstructs(node) {
    if (typeof node.getResultItem === 'function') {
      let id = String(node.getResultItem(registry).id)
      if (Object.prototype.hasOwnProperty.call(constructCounts, id)) constructCounts[id]++
    } else if (node instanceof RecipeMap) {
      node.values().forEach(countConstructs)
    } else {
      node.forEach(countConstructs)
    }
  }
  countConstructs(manager.getRecipes())
  let missingConstructs = Object.keys(constructCounts).filter(id => constructCounts[id] === 0)
  let report = {mode: 'parallel_native_and_cmi', enabled: enabled, skippedByNativeConditions: skipped,
    missing: missing, wrongOutput: wrongOutput, missingRetained: missingRetained,
    constructCounts: constructCounts, missingConstructs: missingConstructs,
    passed: missing.length === 0 && wrongOutput.length === 0 && missingRetained.length === 0 && missingConstructs.length === 0}
  JsonIO.write('kubejs/exported/expedition-pre-steam-audit.json', report)
  console.info(`[Expedition Pre-Steam] auditPassed=${report.passed}, enabled=${enabled}, retainedConstructs=${Object.keys(constructCounts).length}`)
})
