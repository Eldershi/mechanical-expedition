// Allow normal sleeping while wearing the Ring of the Seven Curses.
// Apply on server script reload and synchronize the native option to online clients.
const ExpeditionSleepCursedRing = Java.loadClass('com.aizistral.enigmaticlegacy.items.CursedRing')
const ExpeditionSleepOmniconfig = Java.loadClass('com.aizistral.omniconfig.wrappers.OmniconfigWrapper')
const ExpeditionSleepSuperposition = Java.loadClass('com.aizistral.enigmaticlegacy.handlers.SuperpositionHandler')
ExpeditionSleepCursedRing.disableInsomnia.setValue(true)
ExpeditionSleepSuperposition.executeOnServer(server => {
  const wrapper = ExpeditionSleepOmniconfig.wrapperRegistry.get('enigmaticlegacy-common.omniconf')
  if (wrapper == null) throw new Error('Enigmatic Legacy common config wrapper is missing')
  let synced = 0
  server.getPlayerList().getPlayers().forEach(player => {
    if (ExpeditionSleepOmniconfig.syncWrapperToPlayer(wrapper, player)) synced++
  })
  console.info('[Expedition] Seven Curses insomnia disabled=' + ExpeditionSleepCursedRing.disableInsomnia.getValue() + '; clients synced=' + synced)
})
