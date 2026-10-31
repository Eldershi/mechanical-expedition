// Shorten only BOP high_grass/high_grass_plant in loaded chunks. Other plants are untouched.
const ExpeditionGrassPos = Java.loadClass('net.minecraft.core.BlockPos')
const ExpeditionGrassBlocks = Java.loadClass('net.minecraft.world.level.block.Blocks')

ServerEvents.tick(event => {
  let state = global.expeditionShortGrass
  let cells = 4096
  let sections = 32
  let jobs = 32
  while (cells > 0 && sections > 0 && jobs > 0) {
    if (state.active === null) {
      state.active = state.queue.poll()
      if (state.active === null) break
      jobs--
    }
    let job = state.active
    // getChunkNow returns null instead of generating/loading a chunk.
    let chunk = job.level.getChunkSource().getChunkNow(job.x, job.z)
    if (chunk === null || Number(state.versions.get(chunk)) >= state.version) {
      state.pending.remove(job.key)
      state.slots.release()
      state.active = null
      continue
    }
    let chunkSections = chunk.getSections()
    if (!job.started) {
      job.section = chunkSections.length - 1
      job.started = true
    }
    while (job.section >= 0 && cells > 0 && sections > 0) {
      let section = chunkSections[job.section]
      if (job.cell < 0) {
        sections--
        if (section.hasOnlyAir() || !section.maybeHas(global.expeditionIsHighGrass)) {
          job.section--
          continue
        }
        job.cell = 4095
      }
      // Top down keeps the bottom of each original column distinguishable even
      // when a column crosses a section boundary or spans multiple ticks.
      while (job.cell >= 0 && cells > 0) {
        let index = job.cell--
        cells--
        let x = index & 15
        let z = (index >> 4) & 15
        let y = index >> 8
        if (!global.expeditionIsHighGrass(section.getBlockState(x, y, z))) continue
        let pos = new ExpeditionGrassPos(job.x * 16 + x,
          chunk.getMinBuildHeight() + job.section * 16 + y, job.z * 16 + z)
        let below = job.level.getBlockState(pos.below())
        let grass = ExpeditionGrassBlocks.GRASS.defaultBlockState()
        let replacement = !global.expeditionIsHighGrass(below) && grass.canSurvive(job.level, pos)
          ? grass : ExpeditionGrassBlocks.AIR.defaultBlockState()
        // Update clients/heightmaps, without neighbor cascades or plant-item drops.
        job.level.setBlock(pos, replacement, 18)
      }
      if (job.cell < 0) job.section--
    }
    if (job.section < 0) {
      state.versions.put(chunk, state.version)
      chunk.setUnsaved(true)
      state.pending.remove(job.key)
      state.slots.release()
      state.active = null
    } else break
  }
})

ServerEvents.unloaded(event => {
  // Integrated servers can stop while the game remains open.
  let state = global.expeditionShortGrass
  state.queue.clear()
  state.pending.clear()
  state.versions.clear()
  state.active = null
  state.slots.drainPermits()
  state.slots.release(4096)
  state.overflowWarned = false
})
