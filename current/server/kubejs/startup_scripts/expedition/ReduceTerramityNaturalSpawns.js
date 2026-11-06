// Requires a full game/server restart: Forge native listeners are startup-only.
// Prevent natural and chunk-generation spawns of Terramity fairies and cave gnomes.
// Existing mobs, structure inhabitants and deliberate summons retain their behavior.
const ExpeditionTerramitySpawnRegistries = Java.loadClass('net.minecraftforge.registries.ForgeRegistries')
const ExpeditionTerramityNaturalSpawnKeepChance = 0
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
