// priority: 10000
// Server script. Review/deploy separately; this source does not install itself.
;(function () {
  const System = Java.loadClass('java.lang.System')
  // This must precede GenerationTask initialization, including TaskLoader.loadTask.
  System.setProperty('chunky.maxWorkingCount', '1')
  const UUID = Java.loadClass('java.util.UUID')
  const File = Java.loadClass('java.io.File')
  const Files = Java.loadClass('java.nio.file.Files')
  const Runtime = Java.loadClass('java.lang.Runtime')
  const Class = Java.loadClass('java.lang.Class')
  const Thread = Java.loadClass('java.lang.Thread')
  const OWNER_KEY = 'expedition.idlePregeneration20261020.owner'
  const OWNER = String(UUID.randomUUID())
  System.setProperty(OWNER_KEY, OWNER)
  const CONFIG = 'kubejs/config/idle-pregeneration-20261020.json'
  const STATE = 'kubejs/config/idle-pregeneration-20261020-state.json'
  const STATUS = 'kubejs/exported/idle-pregeneration-20261020-status.json'
  const WORLD = 'minecraft:overworld'
  const RADIUS = 5000
  const QUIET_MS = 60000
  const CHECK_MS = 5000
  const MIN_DISK = 10 * 1024 * 1024 * 1024
  const MAX_WORLD_BYTES = 10 * 1024 * 1024 * 1024
  let chunky = null, api = null, config = null, state = null, disk = null
  let initialized = false, blocked = false, firstCheck = true
  let emptySince = 0, cooldownUntil = 0, lastTick = 0, lastCheck = 0
  let tickGap = 0, lastBadGap = 0, lastReport = 0, reportKey = ''
  let pauseRequested = false, maxWorkingCount = null
  let stateRead = 'not_read', stateWrittenAt = null, ioError = null
  let lastSizeScan = null
  let metrics = { usableDiskBytes: null, usedHeapRatio: null,
    worldBytes: null, worldSizeGuardAt: null, worldSizeScanMs: null }

  function current() { return String(System.getProperty(OWNER_KEY)) === OWNER }
  function now() { return Number(System.nanoTime()) / 1000000 }
  function readJson(path) {
    // Convert Gson/Java values to native JS values, including armed/terminal booleans.
    return JSON.parse(String(JsonIO.readJson(path)))
  }
  function writeJson(path, value) {
    new File(path).getParentFile().mkdirs()
    JsonIO.write(path, value)
  }
  function saveState() {
    state.updatedAtEpochMs = Date.now()
    try {
      writeJson(STATE, state)
      stateWrittenAt = state.updatedAtEpochMs
    } catch (error) {
      ioError = 'state_write_failed: ' + error
      throw new Error(ioError)
    }
  }
  function report(reason, players, error) {
    let time = now()
    let key = reason + ':' + String(error || '')
    if (key === reportKey && time - lastReport < 30000) return
    if (key !== reportKey) {
      if (error) console.error('[Idle Pregeneration] ' + reason + ': ' + error)
      else console.info('[Idle Pregeneration] ' + reason)
    }
    reportKey = key
    lastReport = time
    try {
      writeJson(STATUS, {
        controller: 'idle-pregeneration-20261020', owner: OWNER,
        state: reason, error: error ? String(error) : null,
        world: WORLD, radius: RADIUS, shape: 'circle', pattern: 'concentric',
        centerX: config ? config.centerX : null, centerZ: config ? config.centerZ : null,
        armed: config ? config.armed === true : false, terminal: state ? state.terminal : false,
        stage: state ? state.stage : null, taskSeen: state ? state.taskSeen : false,
        players: players, emptyForMs: emptySince ? Math.max(0, time - emptySince) : 0,
        cooldownRemainingMs: Math.max(0, cooldownUntil - time),
        latestTickGapMs: tickGap, lastBadTickGapMs: lastBadGap,
        maxWorkingCount: maxWorkingCount, usableDiskBytes: metrics.usableDiskBytes,
        usedHeapRatio: metrics.usedHeapRatio,
        worldBytes: metrics.worldBytes, worldSizeGuardAt: metrics.worldSizeGuardAt,
        worldSizeScanMs: metrics.worldSizeScanMs, worldSizeCapBytes: MAX_WORLD_BYTES,
        diskGuard: 'filesystem usable space only; container/panel quota is not visible',
        configPath: CONFIG, statePath: STATE, stateRead: stateRead,
        stateWrittenAtEpochMs: stateWrittenAt, ioError: ioError, atEpochMs: Date.now()
      })
    } catch (failure) {
      // Losing the status audit also disables automatic starts/resumes.
      ioError = 'status_write_failed: ' + failure
      throw new Error(ioError)
    }
  }
  function validCenter(value) {
    return typeof value === 'number' && Number.isFinite(value) &&
      Math.abs(value) <= 29994000 && Math.floor(value) === value
  }
  function worldSize(time) {
    if (lastSizeScan !== null && time - lastSizeScan < 60000) return
    lastSizeScan = time
    let started = now(), bytes = 0, directories = [disk]
    try {
      while (directories.length) {
        let children = directories.pop().listFiles()
        if (children === null) throw new Error('World size guard cannot list a directory')
        for (let i = 0; i < children.length; i++) {
          let child = children[i]
          // Following a symlink could count outside this save or enter a cycle;
          // silently skipping one could undercount the storage bound.
          if (Files.isSymbolicLink(child.toPath())) throw new Error('World size guard refuses symlink: ' + child)
          if (child.isDirectory()) directories.push(child)
          else if (child.isFile()) bytes += Number(child.length())
          if (now() - started > 100) throw new Error('World size scan exceeded 100 ms; controller disabled')
        }
        if (now() - started > 100) throw new Error('World size scan exceeded 100 ms; controller disabled')
      }
      metrics.worldBytes = bytes
      metrics.worldSizeGuardAt = Date.now()
    } finally { metrics.worldSizeScanMs = now() - started }
  }
  function validState(value) {
    return value && value.schema === 1 && typeof value.terminal === 'boolean' &&
      typeof value.taskSeen === 'boolean' && value.world === WORLD && value.stage === RADIUS &&
      validCenter(value.centerX) && validCenter(value.centerZ)
  }
  function matchesAt(task, x, z) {
    let s = task.getSelection()
    return String(s.world().getName()) === WORLD && String(s.shape()) === 'circle' &&
      Number(s.centerX()) === x && Number(s.centerZ()) === z &&
      Number(s.radiusX()) === RADIUS && Number(s.radiusZ()) === RADIUS &&
      String(s.pattern().getType()) === 'concentric'
  }
  function matches(task) { return matchesAt(task, config.centerX, config.centerZ) }
  function pause(running) {
    if (running !== null && matches(running) && !pauseRequested) {
      if (!api.pauseTask(WORLD)) throw new Error('Chunky rejected pauseTask')
      pauseRequested = true
    }
  }
  function fail(error, players) {
    blocked = true
    // No TaskLoader call here; an already initialized wrong worker limit must not
    // lead to task construction. Never touch a different selection or dimension.
    try {
      let owned = validState(state) && !state.terminal && state.taskSeen
      let initialArmed = state === null && config && config.armed === true &&
        validCenter(config.centerX) && validCenter(config.centerZ)
      if (owned || initialArmed) {
        if (chunky === null) chunky = Java.loadClass('org.popcraft.chunky.ChunkyProvider').get()
        if (api === null) api = chunky.getApi()
        let running = chunky.getGenerationTasks().get(WORLD)
        let plan = owned ? state : config
        if (running !== null && matchesAt(running, plan.centerX, plan.centerZ)) {
          // A broken/new config must still allow the previous owned plan to pause.
          if (!api.pauseTask(WORLD)) throw new Error('Chunky rejected emergency pauseTask')
        }
      }
    } catch (pauseError) { console.error('[Idle Pregeneration] emergency pause failed: ' + pauseError) }
    try { report('disabled_error', players, error) }
    catch (reportError) { console.error('[Idle Pregeneration] ' + reportError) }
  }
  function initialize(server) {
    // Load the ownership fingerprint first, so malformed operator config can
    // still pause an already owned task when this reload supersedes old callbacks.
    if (new File(STATE).exists()) {
      try { state = readJson(STATE); stateRead = 'loaded' }
      catch (error) { stateRead = 'failed'; throw new Error('State unreadable; refusing to recreate: ' + error) }
      if (!validState(state)) {
        throw new Error('Invalid persistent state; refusing to recreate')
      }
    } else stateRead = 'absent'
    if (!new File(CONFIG).exists()) {
      writeJson(CONFIG, { armed: false, centerX: null, centerZ: null })
    }
    config = readJson(CONFIG)
    if (!config || typeof config.armed !== 'boolean') throw new Error('Config requires boolean armed')
    if (state && state.terminal) { initialized = true; return }
    if (!validCenter(config.centerX) || !validCenter(config.centerZ)) {
      if (!config.armed && state === null) { initialized = true; return }
      throw new Error('Set integer centerX/centerZ to the verified overworld spawn')
    }
    if (state && (state.centerX !== config.centerX || state.centerZ !== config.centerZ)) {
      throw new Error('Config center differs from persistent plan; refusing a new selection')
    }
    // Reading this static field initializes the class only AFTER the property was set.
    let taskClass = Class.forName('org.popcraft.chunky.GenerationTask', true,
      Thread.currentThread().getContextClassLoader())
    let field = taskClass.getDeclaredField('MAX_WORKING_COUNT')
    field.setAccessible(true)
    maxWorkingCount = Number(field.getInt(null))
    if (maxWorkingCount !== 1) {
      throw new Error('MAX_WORKING_COUNT=' + maxWorkingCount + '; restart with -Dchunky.maxWorkingCount=1')
    }
    chunky = Java.loadClass('org.popcraft.chunky.ChunkyProvider').get()
    api = chunky.getApi()
    let LevelResource = Java.loadClass('net.minecraft.world.level.storage.LevelResource')
    disk = server.getWorldPath(LevelResource.ROOT).toFile().getCanonicalFile()
    if (!disk.exists()) throw new Error('World directory unavailable for disk guard')
    if (state === null && config.armed === true) {
      state = { schema: 1, world: WORLD, centerX: config.centerX, centerZ: config.centerZ,
        stage: RADIUS, taskSeen: false, terminal: false, phase: 'pending', createdAtEpochMs: Date.now() }
      saveState()
    }
    initialized = true
  }
  function check(server, login) {
    if (!current() || blocked) return
    let time = now()
    let players = Number(server.getPlayerList().getPlayers().size())
    if (login) players = Math.max(1, players)
    try {
      if (!initialized) initialize(server)
      if (state && state.terminal) { report('terminal_' + state.phase, players); return }
      if (state === null) { report('unarmed', players); return }
      let running = chunky.getGenerationTasks().get(WORLD)
      if (running === null) pauseRequested = false
      let world = chunky.getServer().getWorld(WORLD).orElse(null)
      if (world === null) throw new Error('Overworld unavailable')
      // GenerationTask's reflected worker limit was validated before this loader call.
      let task = running === null ? chunky.getTaskLoader().loadTask(world).orElse(null) : running
      if (task !== null && !matches(task)) {
        // A different selection is owned by its operator, including a cached old task.
        blocked = true
        report('disabled_selection_mismatch', players, 'Existing overworld task selection does not match; no API action taken')
        return
      }
      if ((task === null && state.taskSeen) || (task !== null && task.isCancelled())) {
        state.terminal = true
        state.phase = 'finished_or_cancelled'
        saveState()
        report('terminal_finished_or_cancelled', players)
        return
      }
      if (task !== null && !state.taskSeen) {
        if (players > 0) pause(running)
        state.taskSeen = true
        state.phase = 'adopted_matching_task'
        saveState()
      }
      if (players > 0) {
        // The login event requests pause before any directory scan or resource
        // sampling. Chunky can drain its existing in-flight request afterwards.
        emptySince = 0
        firstCheck = false
        pause(running)
        report(pauseRequested ? 'pausing_players_online' : 'players_online', players)
        return
      }
      metrics.usableDiskBytes = Number(disk.getUsableSpace())
      let runtime = Runtime.getRuntime()
      metrics.usedHeapRatio = Number(runtime.totalMemory() - runtime.freeMemory()) / Number(runtime.maxMemory())
      worldSize(time)
      let pressure = metrics.worldBytes >= MAX_WORLD_BYTES ? 'world_at_10GiB_cap' :
        metrics.usableDiskBytes < MIN_DISK ? 'disk_below_10GiB' :
        metrics.usedHeapRatio > 0.85 ? 'heap_above_85_percent' : null
      if (pressure !== null) cooldownUntil = Math.max(cooldownUntil, time + QUIET_MS)
      if (players > 0) emptySince = 0
      else if (!emptySince) emptySince = time
      // Reloads reset quiet time and pause the matching task before taking ownership.
      let settling = firstCheck
      firstCheck = false
      let reason = !config.armed ? 'disarmed' : players > 0 ? 'players_online' :
        pressure !== null ? pressure : time < cooldownUntil ? 'cooldown' :
        time - emptySince < QUIET_MS ? 'waiting_60_seconds_empty' : settling ? 'controller_initializing' : null
      if (reason !== null) {
        pause(running)
        report(pauseRequested ? 'pausing_' + reason : reason, players)
        return
      }
      if (running !== null) {
        report(pauseRequested ? 'waiting_for_pause_to_drain' : 'running_empty', players)
        return
      }
      // Persist intent BEFORE any create/resume, so a crash never silently re-creates a missing task.
      state.taskSeen = true
      state.phase = task === null ? 'creation_requested' : 'resume_requested'
      saveState()
      // Check audit storage before starting work as well.
      report(state.phase, players)
      let accepted = task === null ? api.startTask(WORLD, 'circle', config.centerX, config.centerZ,
        RADIUS, RADIUS, 'concentric') : api.continueTask(WORLD)
      if (!accepted) throw new Error('Chunky rejected ' + state.phase + '; automatic retry disabled')
      state.phase = 'tracking'
      saveState()
      report(task === null ? 'started_empty' : 'resumed_empty', players)
    } catch (error) { fail(error, players) }
  }
  PlayerEvents.loggedIn(event => check(event.server, true))
  ServerEvents.tick(event => {
    if (!current() || blocked) return
    let time = now()
    tickGap = lastTick ? time - lastTick : 0
    lastTick = time
    let slow = tickGap > 1000
    if (slow) {
      lastBadGap = tickGap
      cooldownUntil = time + QUIET_MS
    }
    if (slow || !lastCheck || time - lastCheck >= CHECK_MS) {
      lastCheck = time
      check(event.server, false)
    }
  })
})()
