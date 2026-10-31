// Full client/server restart required: native listeners and item registration.
// Keep the dedicated backpack position strict, including Curios' generic-curio fallback.
const ExpeditionEquipmentApi = Java.loadClass('top.theillusivec4.curios.api.CuriosApi')
const ExpeditionEquipmentLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const ExpeditionEquipmentResult = Java.loadClass('net.minecraftforge.eventbus.api.Event$Result')
const ExpeditionCatItems = Java.loadClass('com.github.L_Ender.cataclysm.init.ModItems')
const ExpeditionCatAttributes = Java.loadClass('com.github.L_Ender.cataclysm.init.ModAttribute')
const ExpeditionCatAttributeContainer = Java.loadClass('com.github.L_Ender.cataclysm.items.CuriosItem.AttributeContainer')
const ExpeditionEquipmentOperation = Java.loadClass('net.minecraft.world.entity.ai.attributes.AttributeModifier$Operation')
const ExpeditionEquipmentSlotAttribute = Java.loadClass('top.theillusivec4.curios.api.SlotAttribute')
const expeditionBackpackTag = 'expedition:backpacks'
const expeditionAetherShieldTag = 'aether:accessories_shields'
const expeditionAetherMiscTag = 'aether:accessories_miscellaneous'
const expeditionGenericCurioTag = 'curios:curio'
const expeditionTypedEquipmentTags = {}
;['back', 'backpack', 'belt', 'body', 'bracelet', 'charm', 'hands', 'head', 'necklace',
  'ring', 'mechanisms', 'hostility_curse', 'an_focus', 'bundle', 'feet', 'spellbook',
  'adv_pattern_encoder', 'brooch', 'deep_learner', 'pouch', 'tiab',
  'talisman', 'rune', 'scroll', 'spellstone'].forEach(slot => {
  expeditionTypedEquipmentTags[slot] = 'curios:' + slot
})
function expeditionEquipmentHasTag(stack, tag) {
  // Avoid ItemStack.is(TagKey)/is(Item), which share an SRG name in KubeJS 2001.
  return Ingredient.of('#' + tag).test(stack)
}

StartupEvents.init(() => {
  ExpeditionEquipmentApi.registerCurioPredicate(new ExpeditionEquipmentLocation('expedition:backpack'), result => {
    return expeditionEquipmentHasTag(result.stack(), expeditionBackpackTag)
  })
})

StartupEvents.postInit(() => {
  // Cataclysm checks the identifier before supplying this ring's native attribute.
  ExpeditionCatItems.RING_OF_GRUDGED.get().withAttributes('ring',
    new ExpeditionCatAttributeContainer(ExpeditionCatAttributes.ADDITIONAL_CRITICAL_DAMAGE.get(),
      10, ExpeditionEquipmentOperation.ADDITION))
})

global.expeditionEquipmentAllowed = (slot, stack) => {
  let backpack = expeditionEquipmentHasTag(stack, expeditionBackpackTag)
  // Curios normally accepts any tagged equipment in curio, and curio-tagged items
  // in every other type. Enforce the pack's explicit, separate equipment budgets.
  let validType = slot === 'curio'
    ? expeditionEquipmentHasTag(stack, expeditionGenericCurioTag) && !Object.keys(expeditionTypedEquipmentTags)
      .some(type => expeditionEquipmentHasTag(stack, expeditionTypedEquipmentTags[type]))
    : expeditionTypedEquipmentTags[slot] && expeditionEquipmentHasTag(stack, expeditionTypedEquipmentTags[slot])
  if ((slot === 'backpack' && !backpack) || (backpack && slot !== 'backpack') ||
      expeditionEquipmentHasTag(stack, expeditionAetherShieldTag) ||
      (expeditionEquipmentHasTag(stack, expeditionAetherMiscTag) && slot !== 'curio') || !validType) {
    return false
  }
  return true
}

ForgeEvents.onEvent('top.theillusivec4.curios.api.event.CurioEquipEvent', event => {
  if (!global.expeditionEquipmentAllowed(String(event.getSlotContext().identifier()), event.getStack()))
    event.setResult(ExpeditionEquipmentResult.DENY)
})

ForgeEvents.onEvent('top.theillusivec4.curios.api.event.CurioAttributeModifierEvent', event => {
  // Fix the requested capacities while preserving the four original unlock systems.
  let remove = []
  event.getModifiers().keySet().forEach(attribute => {
    if (attribute instanceof ExpeditionEquipmentSlotAttribute &&
        ['talisman', 'rune', 'scroll', 'spellstone'].indexOf(String(attribute.getIdentifier())) < 0)
      remove.push(attribute)
  })
  remove.forEach(attribute => event.removeAttribute(attribute))
})
