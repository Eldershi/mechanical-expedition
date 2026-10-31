// priority: -99
// Overworld natural weather is global; biomes choose rain, snow or no precipitation.
// Vanilla 1.20.1 samples a 12,000–180,000 tick dry wait and a 12,000–24,000 tick rain.
// Extend only natural dry waits by 5.75. Rain duration and /weather commands stay vanilla.
// With unchanged rain duration, long-run rain starts/time fall to 20% of vanilla in the long-run theoretical mean.
const ExpeditionWeatherGameRules = Java.loadClass('net.minecraft.world.level.GameRules')
const expeditionWeatherDryWaitMultiplier = 5.75

// KubeJS 2001.6.5 fires this AFTER the level tick. Vanilla first reaches rainTime=0,
// then samples the next timer on the following tick. Persistent observations avoid
// multiplying an existing extended timer again after /reload or a server restart.
LevelEvents.tick('minecraft:overworld', event => {
  const level = event.level
  if (!level.getGameRules().getBoolean(ExpeditionWeatherGameRules.RULE_WEATHER_CYCLE)) return
  const weather = level.getLevelData()
  const state = level.persistentData
  let rainTime = weather.getRainTime()
  const naturalDry = !weather.isRaining() && weather.getClearWeatherTime() === 0
  const sampledDryWait = rainTime >= 12000 && rainTime <= 180000

  if (!state.getBoolean('expeditionWeatherDryWaitV1')) {
    // Adopt the current natural dry wait once. Let an existing rain finish normally.
    // A forced /weather clear period has clearWeatherTime>0 and is left untouched.
    if (naturalDry && rainTime > 0 && rainTime <= 180000) {
      rainTime = Math.round(rainTime * expeditionWeatherDryWaitMultiplier)
      weather.setRainTime(rainTime)
    }
    state.putBoolean('expeditionWeatherDryWaitV1', true)
  } else if (naturalDry && sampledDryWait && state.getInt('expeditionWeatherLastRainTime') === 0) {
    rainTime = Math.round(rainTime * expeditionWeatherDryWaitMultiplier)
    weather.setRainTime(rainTime)
  }
  state.putInt('expeditionWeatherLastRainTime', rainTime)
})
