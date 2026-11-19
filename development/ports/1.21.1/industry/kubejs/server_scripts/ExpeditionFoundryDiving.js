const foundryBreatheEvent = Java.loadClass('net.neoforged.neoforge.event.entity.living.LivingBreatheEvent')
const foundryServerPlayer = Java.loadClass('net.minecraft.server.level.ServerPlayer')
const foundryEquipmentSlot = Java.loadClass('net.minecraft.world.entity.EquipmentSlot')
const foundryFluidTags = Java.loadClass('net.minecraft.tags.FluidTags')
const foundryToolStack = Java.loadClass('modernmods.modernfoundry.library.tools.nbt.ToolStack')
const foundryModifierId = Java.loadClass('modernmods.modernfoundry.library.modifiers.ModifierId')
const foundryBacktank = Java.loadClass('com.simibubi.create.content.equipment.armor.BacktankUtil')
const foundryDivingModifier = foundryModifierId.tryParse('cmi:diving')

NativeEvents.onEvent(foundryBreatheEvent, event => {
  const player = event.getEntity()
  if (!(player instanceof foundryServerPlayer) || event.canBreathe() || player.isCreative()
      || player.isSpectator() || String(player.level.dimension) === 'minecraft:the_nether'
      || !player.isEyeInFluid(foundryFluidTags.WATER)) return

  const helmet = player.getItemBySlot(foundryEquipmentSlot.HEAD)
  if (String(helmet.id) !== 'modernfoundry:plate_helmet') return
  const tool = foundryToolStack.from(helmet)
  if (tool.isBroken() || tool.getModifiers().getLevel(foundryDivingModifier) < 1) return

  const tanks = foundryBacktank.getAllWithAir(player)
  if (tanks.isEmpty()) return
  event.setCanBreathe(true)
  event.setConsumeAirAmount(0)
  event.setRefillAirAmount(4)
  if (player.tickCount % 20 === 0) foundryBacktank.consumeAir(player, tanks.get(0), 1)
})
