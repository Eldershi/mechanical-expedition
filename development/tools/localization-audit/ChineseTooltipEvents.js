// Register once on clients, after normal-priority mod tooltip handlers.
if (Platform.isClientEnvironment()) {
  let ExpeditionTooltipKubeJS = Java.loadClass('dev.latvian.mods.kubejs.KubeJS')
  if (ExpeditionTooltipKubeJS.getStartupScriptManager().firstLoad &&
      !global.expeditionChineseTooltipListenerRegistered) {
    let ExpeditionTooltipForge = Java.loadClass('net.minecraftforge.common.MinecraftForge')
    let ExpeditionTooltipPriority = Java.loadClass('net.minecraftforge.eventbus.api.EventPriority')
    let ExpeditionTooltipEvent = Java.loadClass('net.minecraftforge.event.entity.player.ItemTooltipEvent')
    ExpeditionTooltipForge.EVENT_BUS.addListener(ExpeditionTooltipPriority.LOWEST, false,
      ExpeditionTooltipEvent, event => {
        if (typeof global.expeditionTranslateTooltipLines === 'function') {
          global.expeditionTranslateTooltipLines(event.getToolTip())
        }
      })
    global.expeditionChineseTooltipListenerRegistered = true
  }
}
