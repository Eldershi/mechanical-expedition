// Reconcile retained items once; Curios itself returns removed/overflow slots.
const ExpeditionEquipmentMigrationApi = Java.loadClass('top.theillusivec4.curios.api.CuriosApi')
function expeditionReconcileEquipment(player) {
  let optional = ExpeditionEquipmentMigrationApi.getCuriosInventory(player).resolve()
  if (!optional.isPresent()) return {moved: 0, returned: 0}
  let inventory = optional.get()
  inventory.getCurios().forEach((name, handler) => {
    if (['talisman', 'rune', 'scroll', 'spellstone'].indexOf(String(name)) < 0) {
      // Discard saved capacity bonuses from equipment worn before this layout.
      // Curios returns any stacks displaced by the resulting shrink.
      handler.clearModifiers()
      handler.clearCachedModifiers()
      handler.update()
    }
  })
  let pending = []
  inventory.getCurios().forEach((name, handler) => {
    let slot = String(name)
    function collect(stacks, cosmetic) {
      for (let i = 0; i < stacks.getSlots(); i++) {
        let stack = stacks.getStackInSlot(i)
        // Type checks avoid falsely unequipping unique items which are already worn.
        if (!stack.isEmpty() && !global.expeditionEquipmentAllowed(slot, stack)) {
          pending.push({stack: stack.copy(), cosmetic: cosmetic})
          stacks.setStackInSlot(i, Item.of('minecraft:air'))
        }
      }
    }
    collect(handler.getStacks(), false)
    if (handler.hasCosmetic()) collect(handler.getCosmeticStacks(), true)
  })
  let result = {moved: 0, returned: 0}
  pending.forEach(row => {
    let remainder = row.stack
    inventory.getCurios().forEach((name, handler) => {
      if (remainder.isEmpty() || !global.expeditionEquipmentAllowed(String(name), remainder) ||
          (row.cosmetic && !handler.hasCosmetic())) return
      let stacks = row.cosmetic ? handler.getCosmeticStacks() : handler.getStacks()
      for (let i = 0; i < stacks.getSlots() && !remainder.isEmpty(); i++) {
        if (stacks.getStackInSlot(i).isEmpty() && stacks.isItemValid(i, remainder))
          remainder = stacks.insertItem(i, remainder, false)
      }
    })
    if (remainder.isEmpty()) result.moved++
    else {
      inventory.loseInvalidStack(remainder)
      result.returned++
    }
  })
  inventory.handleInvalidStacks()
  return result
}
global.expeditionReconcileEquipment = expeditionReconcileEquipment
PlayerEvents.loggedIn(event => {
  let player = event.player
  if (player.persistentData.expeditionEquipmentLayoutV1) return
  event.server.scheduleInTicks(2, () => {
    if (player.isRemoved()) return
    let result = expeditionReconcileEquipment(player)
    player.persistentData.expeditionEquipmentLayoutV1 = true
    if (result.moved || result.returned)
      player.tell('装备栏已整理：调整 ' + result.moved + ' 件，退回 ' + result.returned + ' 件。')
  })
})
