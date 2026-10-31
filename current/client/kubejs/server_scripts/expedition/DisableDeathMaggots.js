// OPTIONAL: Outside the strict natural-spawn overlay. Do not copy by default.
// Install under kubejs/server_scripts/expedition/ only if death-created maggots
// should also be disabled. Uses the mod's own gamerule; no MOB_SUMMONED blanket.
ServerEvents.loaded(event => {
  event.server.runCommandSilent('gamerule maggotsAppearance false')
})
