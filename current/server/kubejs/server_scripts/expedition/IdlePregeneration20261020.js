// priority: 10000
;(function () {
  const WORLD = 'minecraft:overworld'
  const RADIUS = 5000
  const PATTERN = 'concentric'
  const QUIET_MS = 60000
  const CHECK_MS = 5000
  const CONFIG = 'kubejs/config/idle-pregeneration-20261020.json'
  const STATE = 'kubejs/config/idle-pregeneration-20261020-state.json'
  const STATUS = 'kubejs/exported/idle-pregeneration-20261020-status.json'

  let config, state, chunky
  let initialized = false
  let blocked = false
  let pauseRequested = false
  let emptySince = null
  let lastTick = 0
  let nextCheck = 0
  let reportKey = ''

  function readJson(path) {
    return JSON.parse(String(JsonIO.readString(path)))
  }

  function saveState() {
    state.updatedAtEpochMs = Date.now()
    JsonIO.write(STATE, state)
  }

  function validCenter(value) {
    return Number.isInteger(value) && Math.abs(value) <= 29994000
  }

  function report(reason, players) {
    if (reason === reportKey) return
    JsonIO.write(STATUS, {
      state: reason, world: WORLD, shape: 'circle', radius: RADIUS, pattern: PATTERN,
      centerX: config ? config.centerX : null, centerZ: config ? config.centerZ : null,
      players: players, atEpochMs: Date.now()
    })
    reportKey = reason
    console.info('[Idle Pregeneration] ' + reason)
  }

  function matches(task, plan) {
    const selection = task.getSelection()
    return String(selection.world().getName()) === WORLD &&
      String(selection.shape()) === 'circle' &&
      Number(selection.centerX()) === plan.centerX &&
      Number(selection.centerZ()) === plan.centerZ &&
      Number(selection.radiusX()) === RADIUS && Number(selection.radiusZ()) === RADIUS &&
      String(selection.pattern().getType()) === PATTERN
  }

  function pause(task, plan) {
    if (task === null || pauseRequested || !matches(task, plan)) return
    pauseRequested = chunky.getApi().pauseTask(WORLD)
    if (!pauseRequested && chunky.getApi().isRunning(WORLD)) throw new Error('Chunky rejected pause')
  }

  function initialize() {
    state = readJson(STATE)
    if (state !== null && (state.schema !== 1 || state.world !== WORLD || state.stage !== RADIUS ||
        typeof state.taskSeen !== 'boolean' || typeof state.terminal !== 'boolean' ||
        !validCenter(state.centerX) || !validCenter(state.centerZ))) {
      throw new Error('Invalid saved pregeneration state')
    }
    const savedConfig = readJson(CONFIG)
    config = savedConfig === null ? { armed: false, centerX: null, centerZ: null } : savedConfig
    if (typeof config.armed !== 'boolean') throw new Error('Config requires boolean armed')
    if (config.armed && (!validCenter(config.centerX) || !validCenter(config.centerZ))) {
      throw new Error('Set centerX and centerZ to the current overworld spawn before enabling')
    }
    if (state !== null || config.armed) {
      chunky = Java.loadClass('org.popcraft.chunky.ChunkyProvider').get()
    }
    if (config.armed && state !== null &&
        (state.centerX !== config.centerX || state.centerZ !== config.centerZ)) {
      throw new Error('Configured center differs from saved pregeneration state')
    }
    initialized = true
  }

  function check(server, now, login) {
    const players = Math.max(login ? 1 : 0, Number(server.getPlayerList().getPlayers().size()))
    if (players > 0) emptySince = null
    try {
      if (!initialized) initialize()
      if (state === null ? !config.armed : state.terminal) return
      let plan = state === null ? config : state
      let running = chunky.getGenerationTasks().get(WORLD)
      if (running === null) pauseRequested = false
      if (!config.armed || players > 0) {
        pause(running, plan)
        report(!config.armed ? 'disarmed' : pauseRequested ? 'pausing_players_online' : 'players_online', players)
        return
      }
      let spawn = server.overworld().getSharedSpawnPos()
      if (Number(spawn.getX()) !== plan.centerX || Number(spawn.getZ()) !== plan.centerZ) {
        throw new Error('Configured center differs from the current overworld spawn')
      }
      if (emptySince === null) emptySince = now
      if (now - emptySince < QUIET_MS) {
        pause(running, plan)
        report('waiting_60_seconds_empty', players)
        return
      }
      if (running !== null) {
        if (!matches(running, plan)) throw new Error('Overworld already has a different Chunky task')
        report('running_empty', players)
        return
      }
      let world = chunky.getServer().getWorld(WORLD).orElse(null)
      if (world === null) throw new Error('Overworld unavailable in Chunky')
      let saved = chunky.getTaskLoader().loadTask(world).orElse(null)
      if (saved !== null && !matches(saved, plan)) throw new Error('Overworld has a different saved Chunky task')
      if ((saved === null && state !== null && state.taskSeen) || (saved !== null && saved.isCancelled())) {
        state = { schema: 1, world: WORLD, stage: RADIUS, centerX: plan.centerX, centerZ: plan.centerZ,
          taskSeen: true, terminal: true }
        saveState()
        report('finished_or_cancelled', players)
        return
      }
      state = { schema: 1, world: WORLD, stage: RADIUS, centerX: plan.centerX, centerZ: plan.centerZ,
        taskSeen: true, terminal: false }
      // Persist the selection before invoking Chunky. A restart uses Chunky's saved progress.
      saveState()
      let api = chunky.getApi()
      let accepted = saved === null
        ? api.startTask(WORLD, 'circle', plan.centerX, plan.centerZ, RADIUS, RADIUS, PATTERN)
        : api.continueTask(WORLD)
      if (!accepted) throw new Error('Chunky rejected start or resume')
      report(saved === null ? 'started_empty' : 'resumed_empty', players)
    } catch (error) {
      blocked = true
      if (chunky) {
        try { pause(chunky.getGenerationTasks().get(WORLD), state || config) }
        catch (pauseError) { console.error('[Idle Pregeneration] pause failed: ' + pauseError) }
      }
      console.error('[Idle Pregeneration] disabled: ' + error)
    }
  }

  PlayerEvents.loggedIn(event => {
    if (!blocked) check(event.server, Date.now(), true)
  })

  ServerEvents.tick(event => {
    if (blocked) return
    const now = Date.now()
    const tickGap = now - lastTick
    lastTick = now
    if (tickGap < 0 || tickGap > 1000) {
      emptySince = null
      nextCheck = now
    }
    if (now >= nextCheck) {
      nextCheck = now + CHECK_MS
      check(event.server, now, false)
    }
  })
})()
