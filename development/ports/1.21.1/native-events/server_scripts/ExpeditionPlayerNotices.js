const expeditionNoticeComponent = Java.loadClass('net.minecraft.network.chat.Component')
const expeditionNoticeGameRules = Java.loadClass('net.minecraft.world.level.GameRules')
const expeditionNoticeServerLevel = Java.loadClass('net.minecraft.server.level.ServerLevel')
const expeditionNoticeServerPlayer = Java.loadClass('net.minecraft.server.level.ServerPlayer')
const expeditionNoticeSoundEvent = Java.loadClass('net.minecraft.sounds.SoundEvent')
const expeditionNoticeSoundSource = Java.loadClass('net.minecraft.sounds.SoundSource')
const expeditionNoticeLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const expeditionNoticeDragonSound = expeditionNoticeSoundEvent.createVariableRangeEvent(
  expeditionNoticeLocation.parse('cmi:dragon_death')
)
const expeditionNoticeEntityLeave = Java.loadClass('net.neoforged.neoforge.event.entity.EntityLeaveLevelEvent')
const expeditionNoticeRemovalReason = Java.loadClass('net.minecraft.world.entity.Entity$RemovalReason')
const expeditionNoticeDragon = Java.loadClass('net.minecraft.world.entity.boss.enderdragon.EnderDragon')
const expeditionNoticeLocalDate = Java.loadClass('java.time.LocalDate')
const expeditionNoticeChatFormatting = Java.loadClass('net.minecraft.ChatFormatting')

ServerEvents.loaded(event => {
  const rule = event.server.getGameRules().getRule(expeditionNoticeGameRules.RULE_LAVA_SOURCE_CONVERSION)
  if (!rule.get()) rule.set(true, event.server)
})

PlayerEvents.loggedIn(event => {
  const player = event.player
  const welcome = expeditionNoticeComponent.translatableWithFallback(
    'message.cmi.welcome', 'Welcome to CMI, %s!', player.getName()
  )
  player.serverLevel().players.forEach(other => other.sendSystemMessage(welcome))

  const date = expeditionNoticeLocalDate.now()
  const month = date.getMonthValue()
  if (date.getDayOfMonth() !== 1 || (month !== 4 && month !== 10)) return
  event.server.scheduleInTicks(5, () => {
    if (player.isRemoved()) return
    const greeting = month === 4
      ? expeditionNoticeComponent.translatableWithFallback('message.expedition.april_fools', 'Happy April Fools’ Day!')
      : expeditionNoticeComponent.translatableWithFallback('message.cmi.chinese_national_day', 'Happy National Day!')
        .withStyle(expeditionNoticeChatFormatting.RED)
    player.sendSystemMessage(greeting)
  })
})

NativeEvents.onEvent(expeditionNoticeEntityLeave, event => {
  const level = event.getLevel()
  const entity = event.getEntity()
  if (!(level instanceof expeditionNoticeServerLevel) || !(entity instanceof expeditionNoticeDragon)
      || !expeditionNoticeRemovalReason.KILLED.equals(entity.getRemovalReason())) return

  level.players.forEach(player => {
    if (!(player instanceof expeditionNoticeServerPlayer)) return
    const stages = player.getStages()
    if (stages.has('dragon_death')) return
    stages.add('dragon_death')
    level.playSound(null, player.getX(), player.getY(), player.getZ(), expeditionNoticeDragonSound,
      expeditionNoticeSoundSource.PLAYERS, 0.25, 1)
    player.sendSystemMessage(expeditionNoticeComponent.translatable('entity.minecraft.ender_dragon')
      .append(expeditionNoticeComponent.translatableWithFallback('message.expedition.dragon_hunted', ' — hunt complete')))
  })
})
