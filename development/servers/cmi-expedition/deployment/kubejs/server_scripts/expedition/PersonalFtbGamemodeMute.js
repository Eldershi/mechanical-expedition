// Server-only, reloadable with `kubejs reload server_scripts`.
// Coupled to expedition-ftb-action-announcements 1.0.0's public observer API.
// Pre-observe only Eldershi's exact FTB gamemode leaf. Its original handler
// still runs once; the addon's duplicate-observation guard skips broadcasting.
const ExpeditionFtbMuteObserver = Java.loadClass('expedition.ftb.SuccessfulFtbAction')
const ExpeditionFtbMuteState = Java.loadClass('expedition.ftb.SuccessfulFtbAction$State')
const ExpeditionFtbMutePlayer = Java.loadClass('net.minecraft.server.level.ServerPlayer')
const ExpeditionFtbMuteCommand = Java.loadClass('net.minecraftforge.event.CommandEvent')
const ExpeditionFtbMutePriority = Java.loadClass('net.minecraftforge.eventbus.api.EventPriority')
const expeditionFtbMutedSnapshot = new ExpeditionFtbMuteState('muted', '')

// EventJS unregisters server NativeEvents handlers before each scripts reload.
NativeEvents.onEvent(ExpeditionFtbMutePriority.HIGH, false, ExpeditionFtbMuteCommand, event => {
  if (event.isCanceled()) return
  const parse = event.getParseResults()
  const nodes = parse.getContext().getNodes()
  if (nodes.size() !== 2 || String(nodes.get(0).getNode().getName()) !== 'ftblibrary' ||
      String(nodes.get(1).getNode().getName()) !== 'gamemode') return
  ExpeditionFtbMuteObserver.observe(parse, source => {
    const player = source.getEntity()
    return player instanceof ExpeditionFtbMutePlayer && source.hasPermission(2) &&
      String(player.getGameProfile().getName()) === 'Eldershi'
  }, (source, action) => expeditionFtbMutedSnapshot, (source, state) => {})
})
console.info('[Expedition FTB] Eldershi gamemode announcement mute enabled')
