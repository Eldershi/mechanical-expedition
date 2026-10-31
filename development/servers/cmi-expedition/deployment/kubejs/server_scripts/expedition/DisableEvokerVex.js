// Server-only; /reload applies this rule without restarting the server.
// Keep ownerless vexes and other mods' summons available.
EntityEvents.spawned('minecraft:vex', event => {
  let owner = event.entity.getOwner()
  if (owner && String(owner.type) === 'minecraft:evoker') {
    event.cancel()
  }
})
