// priority: -1290
// Scorched Guns 2 0.5.5 declares an unused C key in this native recipe.
// Create rejects the entire recipe. Remove only that unused declaration before
// SelectedParallelRecipes captures the retained baseline; actual inputs stay intact.
// Official source JAR SHA256: f339dd8444eaf4623449cd11db092beb1f02f14f5d03045a0394070b0ea50170
let equipmentRepairRecipeId = 'scguns:create/mechanical_crafting/jr_wristbreaker'
let equipmentRepairExpected = {"type":"create:mechanical_crafting","conditions":[{"type":"forge:mod_loaded","modid":"create"}],"acceptMirrored":true,"key":{"Q":{"item":"scguns:gun_grip"},"L":{"item":"scguns:rapid_firing_unit"},"R":{"item":"scguns:heavy_gun_parts"},"J":{"item":"scguns:heavy_gun_barrel"},"M":{"item":"scguns:treated_brass_ingot"},"X":{"item":"scguns:treated_brass_blueprint"},"K":{"item":"scguns:treated_brass_gun_frame"},"A":{"item":"scguns:gun_magazine"},"C":{"tag":"minecraft:planks"}},"pattern":["MKX","LRJ","Q A"],"result":{"item":"scguns:jr_wristbreaker"}}

function equipmentRepairCanonical(node) {
  if (node == null || typeof node !== 'object') return JSON.stringify(node)
  if (Array.isArray(node)) return '[' + node.map(equipmentRepairCanonical).join(',') + ']'
  return '{' + Object.keys(node).sort().map(key => JSON.stringify(key) + ':' + equipmentRepairCanonical(node[key])).join(',') + '}'
}

ServerEvents.recipes(event => {
  let report = {id: equipmentRepairRecipeId, applied: false, status: 'absent_or_already_repaired'}
  event.forEachRecipe({id: equipmentRepairRecipeId}, recipe => {
    // A local or future upstream replacement must take precedence over this fix.
    if (recipe.newRecipe || recipe.hasChanged()) {
      report.status = 'retained_modified_recipe'
      return
    }
    let json = JSON.parse(String(recipe.json))
    if (equipmentRepairCanonical(json) !== equipmentRepairCanonical(equipmentRepairExpected)) {
      report.status = 'retained_different_native_recipe'
      return
    }
    delete json.key.C
    event.remove({id: equipmentRepairRecipeId})
    event.custom(json).id(equipmentRepairRecipeId)
    report.applied = true
    report.status = 'removed_unused_key_C'
    report.pattern = json.pattern
    report.inputs = json.key
    console.info('[Equipment Native Recipe Repair] removed unused C declaration from ' + equipmentRepairRecipeId)
  })
  JsonIO.write('kubejs/exported/expedition-equipment-native-repair.json', report)
})
