// Disable naughtiness accumulation, warnings, and punishment summons.
// Krampus and his henchmen retain their natural spawning rules.
ServerEvents.loaded(event => {
  event.server.runCommandSilent('gamerule naughtinessMechanics false')
})
