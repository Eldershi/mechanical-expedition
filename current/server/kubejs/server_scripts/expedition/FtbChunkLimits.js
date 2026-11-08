// Reload the world configuration once after server scripts load.
// FTB Chunks owns quota calculation and sends changed limits to online members.
const ExpeditionChunkConfig = Java.loadClass('dev.ftb.mods.ftbchunks.FTBChunksWorldConfig')
const ExpeditionChunkConfigUtil = Java.loadClass('dev.ftb.mods.ftblibrary.snbt.config.ConfigUtil')
const ExpeditionChunkManager = Java.loadClass('dev.ftb.mods.ftbchunks.data.ClaimedChunkManagerImpl')
let expeditionChunkLimitsPending = true

ServerEvents.tick(event => {
  if (!expeditionChunkLimitsPending) return
  expeditionChunkLimitsPending = false
  try {
    var expeditionFtbConfigDirectory = event.server.getWorldPath(ExpeditionChunkConfigUtil.SERVER_CONFIG_DIR)
    ExpeditionChunkConfigUtil.loadDefaulted(ExpeditionChunkConfig.CONFIG, expeditionFtbConfigDirectory, 'ftbchunks')
    var expeditionFtbManager = ExpeditionChunkManager.getInstance()
    expeditionFtbManager.getTeamManager().getTeams().forEach(team => {
      var expeditionFtbTeamData = expeditionFtbManager['getOrCreateData(dev.ftb.mods.ftbteams.api.Team)'](team)
      expeditionFtbTeamData.updateLimits()
      console.info('[Expedition FTB Chunks] team=' + team.getId() + ' max_force_loaded=' + expeditionFtbTeamData.getMaxForceLoadChunks())
    })
    console.info('[Expedition FTB Chunks] reloaded base=' + ExpeditionChunkConfig.MAX_FORCE_LOADED_CHUNKS.get() + ' hard_team_limit=' + ExpeditionChunkConfig.HARD_TEAM_FORCE_LIMIT.get())
  } catch (error) {
    console.error('[Expedition FTB Chunks] reload failed: ' + error)
  }
})
