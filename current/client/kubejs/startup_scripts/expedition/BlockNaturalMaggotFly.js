// Requires a full client/server restart: Forge native listeners are startup-only.
// Scope: Born in Chaos, NATURAL and CHUNK_GENERATION only.
// Zombie deaths use MOB_SUMMONED and are deliberately preserved here.
const ExpeditionNaturalSpawnRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')

ForgeEvents.onEvent('net.minecraftforge.event.entity.living.MobSpawnEvent$FinalizeSpawn', event => {
  let reason = String(event.getSpawnType().name())
  if (reason !== 'NATURAL' && reason !== 'CHUNK_GENERATION') return

  let id = String(ExpeditionNaturalSpawnRegistries.ENTITY_TYPES.getKey(event.getEntity().getType()))
  if (id === 'born_in_chaos_v1:maggot' || id === 'born_in_chaos_v1:corpse_fly') {
    // setCanceled(true) alone only skips initialization; this blocks the spawn.
    event.setSpawnCancelled(true)
  }
})
