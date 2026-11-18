StartupEvents.registry('item', event => {
  event.create('cmi:laser_diode')
    .displayName('Quartz Diode')
    .texture('create:item/electron_tube')
  event.create('cmi:chromeplated_steel_gear')
    .displayName('Chrome-plated Steel Gear')
    .texture('cmi:item/material/color/gear/gear')
    .color(0, 0xBCC7CE)
})
StartupEvents.registry('fluid', event => {
  event.create('cmi:plating_solution')
    .displayName('Chromium Plating Solution')
    .stillTexture('minecraft:block/water_still')
    .flowingTexture('minecraft:block/water_flow')
    .tint(0xBB9900)
    .tag('cmi:plating_solution')
})

const ExpeditionKnifeItem = Java.loadClass('vectorwing.farmersdelight.common.item.KnifeItem')
const ExpeditionItemProperties = Java.loadClass('net.minecraft.world.item.Item$Properties')
const ExpeditionDiggerItem = Java.loadClass('net.minecraft.world.item.DiggerItem')
const ExpeditionKnifeTier = Java.loadClass('net.minecraft.world.item.Tiers').NETHERITE
const ExpeditionKnifeRarity = Java.loadClass('net.minecraft.world.item.Rarity')
const ExpeditionDataComponents = Java.loadClass('net.minecraft.core.component.DataComponents')
const ExpeditionUnbreakable = Java.loadClass('net.minecraft.world.item.component.Unbreakable')

StartupEvents.registry('item', event => {
  event.createCustom('cmi:super_knife', () => new ExpeditionKnifeItem(
    ExpeditionKnifeTier, new ExpeditionItemProperties()
      .rarity(ExpeditionKnifeRarity.EPIC)
      .attributes(ExpeditionDiggerItem.createAttributes(ExpeditionKnifeTier, 0.5, -2.0))
      .component(ExpeditionDataComponents.UNBREAKABLE, new ExpeditionUnbreakable(false))
  ))
})
StartupEvents.registry('fluid', event => {
  for (const [name, color] of [['ink', 0x262836], ['hyper_experience', 0x74BE43]]) {
    event.create('cmi:' + name)
      .stillTexture('minecraft:block/water_still')
      .flowingTexture('minecraft:block/water_flow')
      .tint(color)
  }
})
