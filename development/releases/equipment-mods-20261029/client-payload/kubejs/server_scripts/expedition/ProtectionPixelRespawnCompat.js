// Protection Pixel 2.2.1 subtracts retained armor-plate bonuses on respawn,
// although Forge's replacement player does not inherit those base attributes.
// Cancel only that subtraction; ordinary equipment changes still apply bonuses.
let expeditionPpRespawnAttributes = Java.loadClass('net.minecraft.world.entity.ai.attributes.Attributes')
let expeditionPpRespawnModList = Java.loadClass('net.minecraftforge.fml.ModList')
let expeditionPpRespawnList = Java.loadClass('java.util.ArrayList')
let expeditionPpRespawnContainer = expeditionPpRespawnModList.get().getModContainerById('protection_pixel').orElse(null)
let expeditionPpRespawnEnabled = expeditionPpRespawnContainer != null
  && String(expeditionPpRespawnContainer.getModInfo().getVersion()) === '2.2.1'

PlayerEvents.respawned(event => {
  if (!expeditionPpRespawnEnabled) return
  let player = event.player
  let slots = new expeditionPpRespawnList(player.getArmorSlots())
  let armorDelta = 0, toughnessDelta = 0
  for (let i = 0; i < slots.size(); i++) {
    let stack = slots.get(i)
    if (stack.isEmpty() || !stack.hasTag('protection_pixel:protection')) continue
    let tag = stack.nbt
    if (tag == null) continue
    let armor = Number(tag.platearmor || 0)
    let toughness = Number(tag.platetoughness || 0)
    if (Number.isFinite(armor)) armorDelta += armor
    if (Number.isFinite(toughness)) toughnessDelta += toughness
  }
  if (armorDelta === 0 && toughnessDelta === 0) return
  // One immediate delta per respawn event, preserving other mods' base values.
  let armorAttribute = player.getAttribute(expeditionPpRespawnAttributes.ARMOR)
  let toughnessAttribute = player.getAttribute(expeditionPpRespawnAttributes.ARMOR_TOUGHNESS)
  if (armorAttribute != null) armorAttribute.baseValue += armorDelta
  if (toughnessAttribute != null) toughnessAttribute.baseValue += toughnessDelta
  console.info('[Protection Pixel Respawn Compat] ' + player.getGameProfile().getName()
    + ' armor +' + armorDelta + ', toughness +' + toughnessDelta)
})
