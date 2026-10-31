// priority: 1000
// SC 0.5.5 registers create_mod_loaded only on the client. Import its two
// otherwise missing dedicated-server recipes before CMI's recipe events so
// local removals/replacements still take precedence. Native cost/time/xp/IDs stay.
// Official source JAR SHA256: f339dd8444eaf4623449cd11db092beb1f02f14f5d03045a0394070b0ea50170
let equipmentEarlyScVersion = '0.5.5'
let equipmentEarlyScRecipes = [{"id":"scguns:create/anthralite_ingot_from_smelting_crushed_raw_anthralite","json":{"type":"minecraft:smelting","category":"misc","group":"anthralite_ingot","cookingtime":200,"experience":0.7,"ingredient":{"item":"scguns:crushed_raw_anthralite"},"result":"scguns:anthralite_ingot","conditions":[{"type":"forge:mod_loaded","modid":"create"}]}},{"id":"scguns:create/anthralite_ingot_from_blasting_crushed_raw_anthralite","json":{"type":"minecraft:blasting","category":"misc","group":"anthralite_ingot","cookingtime":100,"experience":0.7,"ingredient":{"item":"scguns:crushed_raw_anthralite"},"result":"scguns:anthralite_ingot","conditions":[{"type":"forge:mod_loaded","modid":"create"}]}}]

ServerEvents.recipes(event => {
  let mods = Java.loadClass('net.minecraftforge.fml.ModList').get()
  let report = {expectedVersion: equipmentEarlyScVersion, applied: [], retained: [], status: 'mods_or_version_not_applicable'}
  if (!mods.isLoaded('scguns') || !mods.isLoaded('create')) {
    JsonIO.write('kubejs/exported/expedition-equipment-early-native.json', report)
    return
  }
  let installedVersion = String(mods.getModContainerById('scguns').get().getModInfo().getVersion())
  report.installedVersion = installedVersion
  if (installedVersion !== equipmentEarlyScVersion) {
    JsonIO.write('kubejs/exported/expedition-equipment-early-native.json', report)
    return
  }
  report.status = 'checked'
  equipmentEarlyScRecipes.forEach(row => {
    let exists = false
    event.forEachRecipe({id: row.id}, recipe => { exists = true })
    event.addedRecipes.forEach(recipe => {
      if (recipe.newRecipe && !recipe.removed && String(recipe.getOrCreateId()) === row.id) exists = true
    })
    if (exists) {
      report.retained.push(row.id)
      return
    }
    event.custom(JSON.parse(JSON.stringify(row.json))).id(row.id)
    report.applied.push(row.id)
    console.info('[Equipment Early Native Recipes] restored ' + row.id + ' with equivalent forge:mod_loaded condition')
  })
  JsonIO.write('kubejs/exported/expedition-equipment-early-native.json', report)
})
