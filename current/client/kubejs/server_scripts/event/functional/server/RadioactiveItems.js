// Expedition compatibility: schedule by the individual player, never a shared counter.
(() => {
const radiationManager = Java.loadClass('mekanism.api.radiation.IRadiationManager').INSTANCE
PlayerEvents.tick(event => {
    const { player, level } = event
    if (level.isClientSide() || player.isCreative() || player.isFake() || player.isSpectator()) return
    if (player.tickCount % 10 !== 0) return
    let hasRadioactive = false
    for (let stack of player.inventory.items) {
        if (!stack.isEmpty() && stack.hasTag('cmi:radioactive_items')) {
            hasRadioactive = true
            break
        }
    }
    if (hasRadioactive) {
        radiationManager.radiate(player, 0.00000001)
    }
})
})()
