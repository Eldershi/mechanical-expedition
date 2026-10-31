// Disable proximity aggression added by the Ring of the Seven Curses.
// Enigmatic Legacy 2.30.1: curioTick contains only the second-curse logic.
// Native NeutralMob blacklist covers vanilla and modded types. Piglin's separate
// branch ignores that blacklist, so also remove its proximity/through-wall range.
// The Enderman attraction branch has its own range and probability.
// Reapplied on startup and server_scripts reload; no per-tick entity mutations.
const ExpeditionPeaceRing = Java.loadClass('com.aizistral.enigmaticlegacy.items.CursedRing')
const ExpeditionPeaceRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
const ExpeditionPeaceOmniconfig = Java.loadClass('com.aizistral.omniconfig.wrappers.OmniconfigWrapper')
const ExpeditionPeaceSuperposition = Java.loadClass('com.aizistral.enigmaticlegacy.handlers.SuperpositionHandler')

function expeditionApplySevenCursesPeace(server) {
  const keys = ExpeditionPeaceRegistries.ENTITY_TYPES.getKeys()
  keys.forEach(key => {
    if (!ExpeditionPeaceRing.neutralAngerBlacklist.contains(key)) {
      ExpeditionPeaceRing.neutralAngerBlacklist.add(key)
    }
  })
  // setValue directly sets the runtime value; editing omniconf alone would
  // clamp these ranges to 4/8 and the Enderman probability to 0.01 on startup.
  ExpeditionPeaceRing.neutralAngerRange.setValue(0)
  ExpeditionPeaceRing.neutralXRayRange.setValue(0)
  ExpeditionPeaceRing.endermenRandomportRange.setValue(0)
  ExpeditionPeaceRing.endermenRandomportFrequency.setValue(0)

  let missing = 0
  keys.forEach(key => {
    if (!ExpeditionPeaceRing.neutralAngerBlacklist.contains(key)) missing++
  })
  const status = {
    registeredTypes: keys.size(),
    missingBlacklistTypes: missing,
    neutralAngerRange: ExpeditionPeaceRing.neutralAngerRange.getValue(),
    neutralXRayRange: ExpeditionPeaceRing.neutralXRayRange.getValue(),
    endermenRandomportRange: ExpeditionPeaceRing.endermenRandomportRange.getValue(),
    endermenRandomportFrequency: ExpeditionPeaceRing.endermenRandomportFrequency.getValue(),
    clientsSynced: 0
  }
  status.applied = missing === 0 && status.neutralAngerRange === 0 &&
    status.neutralXRayRange === 0 && status.endermenRandomportRange === 0 &&
    status.endermenRandomportFrequency === 0
  if (!status.applied) throw new Error('Seven Curses neutral peace verification failed')
  const wrapper = ExpeditionPeaceOmniconfig.wrapperRegistry.get('enigmaticlegacy-common.omniconf')
  if (wrapper != null) {
    server.getPlayerList().getPlayers().forEach(player => {
      if (ExpeditionPeaceOmniconfig.syncWrapperToPlayer(wrapper, player)) status.clientsSynced++
    })
  }
  JsonIO.write('kubejs/exported/seven-curses-neutral-peace.json', status)
  console.info('[Expedition] Seven Curses neutral peace applied=' + status.applied +
    '; entity types=' + status.registeredTypes + '; missing=' + missing +
    '; anger=0; xray=0; endermanRange=0; endermanFrequency=0; clients synced=' + status.clientsSynced)
}

ServerEvents.loaded(event => expeditionApplySevenCursesPeace(event.server))
ExpeditionPeaceSuperposition.executeOnServer(server => {
  server.execute(() => expeditionApplySevenCursesPeace(server))
})
