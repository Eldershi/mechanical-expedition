// Requires a full game/server restart: Forge native listeners are startup-only.
// Terramity Gnome (cave_gnome) and green/blue/pink fairies: keep 5% of
// otherwise valid NATURAL / CHUNK_GENERATION spawn attempts (95% rejected).
// Existing mobs, bosses, Royal Gnomes, spawners, eggs, commands, breeding,
// fairy bottles and all other summon methods retain their original behavior.
const ExpeditionTerramitySpawnRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
const ExpeditionTerramityNaturalSpawnKeepChance = 0.05
const ExpeditionTerramityRareNaturalMobs = [
  'terramity:cave_gnome',
  'terramity:green_fairy',
  'terramity:blue_fairy',
  'terramity:pink_fairy'
]

ForgeEvents.onEvent('net.minecraftforge.event.entity.living.MobSpawnEvent$FinalizeSpawn', event => {
  let reason = String(event.getSpawnType().name())
  if (reason !== 'NATURAL' && reason !== 'CHUNK_GENERATION') return

  let id = String(ExpeditionTerramitySpawnRegistries.ENTITY_TYPES.getKey(event.getEntity().getType()))
  if (ExpeditionTerramityRareNaturalMobs.indexOf(id) < 0) return

  if (Math.random() >= ExpeditionTerramityNaturalSpawnKeepChance) {
    // Cancel the spawn itself. setCanceled(true) would only skip initialization.
    event.setSpawnCancelled(true)
  }
})
