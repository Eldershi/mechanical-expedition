// Restart the client/server: Forge listeners are registered during startup.
// BOP's grassland high_grass is a real growing column (up to six blocks at generation).
const ExpeditionGrassBOP = Java.loadClass('biomesoplenty.api.block.BOPBlocks')
const ExpeditionGrassLevelChunk = Java.loadClass('net.minecraft.world.level.chunk.LevelChunk')
const ExpeditionGrassResult = Java.loadClass('net.minecraftforge.eventbus.api.Event$Result')
const ExpeditionGrassCollections = Java.loadClass('java.util.Collections')
const ExpeditionGrassWeakMap = Java.loadClass('java.util.WeakHashMap')
const ExpeditionGrassConcurrentMap = Java.loadClass('java.util.concurrent.ConcurrentHashMap')
const ExpeditionGrassConcurrentQueue = Java.loadClass('java.util.concurrent.ConcurrentLinkedQueue')
const ExpeditionGrassSemaphore = Java.loadClass('java.util.concurrent.Semaphore')

global.expeditionShortGrass = {
  version: 1,
  marker: 'expedition_short_grass',
  versions: ExpeditionGrassCollections.synchronizedMap(new ExpeditionGrassWeakMap()),
  queue: new ExpeditionGrassConcurrentQueue(),
  pending: new ExpeditionGrassConcurrentMap(),
  slots: new ExpeditionGrassSemaphore(4096),
  active: null,
  overflowWarned: false
}

global.expeditionIsHighGrass = state => {
  let block = state.getBlock()
  return block === ExpeditionGrassBOP.HIGH_GRASS.get() || block === ExpeditionGrassBOP.HIGH_GRASS_PLANT.get()
}

// ChunkAccess has no persistentData in Forge/KubeJS 1.20.1. Keep a weak, synchronized
// runtime cache, and serialize only this migration's version in the chunk's own NBT.
ForgeEvents.onEvent('net.minecraftforge.event.level.ChunkDataEvent$Load', event => {
  let chunk = event.getChunk()
  if (chunk instanceof ExpeditionGrassLevelChunk) {
    global.expeditionShortGrass.versions.put(chunk, event.getData().getInt(global.expeditionShortGrass.marker))
  }
})
ForgeEvents.onEvent('net.minecraftforge.event.level.ChunkDataEvent$Save', event => {
  let state = global.expeditionShortGrass
  let version = state.versions.get(event.getChunk())
  if (version !== null && Number(version) >= state.version) {
    event.getData().putInt(state.marker, state.version)
  }
})

ForgeEvents.onEvent('net.minecraftforge.event.level.ChunkEvent$Load', event => {
  let chunk = event.getChunk()
  let level = event.getLevel()
  let state = global.expeditionShortGrass
  if (level.isClientSide() || !(chunk instanceof ExpeditionGrassLevelChunk) ||
      Number(state.versions.get(chunk)) >= state.version) return
  let pos = chunk.getPos()
  let key = String(level.dimension) + ',' + pos.x + ',' + pos.z
  if (!state.slots.tryAcquire()) {
    // Never retain chunks or grow the queue without a bound. A later chunk load retries.
    if (!state.overflowWarned) {
      console.warn('[Expedition Short Grass] Migration queue full; deferred chunks retry when reloaded.')
      state.overflowWarned = true
    }
    return
  }
  if (state.pending.putIfAbsent(key, true) !== null) {
    state.slots.release()
    return
  }
  // Store coordinates and the level, never a chunk reference or a forced chunk ticket.
  state.queue.add({ level: level, x: pos.x, z: pos.z, key: key, section: -1, cell: -1, started: false })
})

ForgeEvents.onEvent('net.minecraftforge.event.level.BlockEvent$CropGrowEvent$Pre', event => {
  // BOP passes the destination (air above the head), not the grass head, to this hook.
  let below = event.getLevel().getBlockState(event.getPos().below())
  if (below.getBlock() === ExpeditionGrassBOP.HIGH_GRASS.get()) event.setResult(ExpeditionGrassResult.DENY)
})
