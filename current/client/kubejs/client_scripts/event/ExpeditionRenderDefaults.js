// Apply on the next normal launch, once per client-script load.
// Later manual video/HUD changes stay usable; nothing is forced every frame.
let expeditionRenderDefaultsApplied = false
ClientEvents.tick(event => {
  if (expeditionRenderDefaultsApplied) return
  expeditionRenderDefaultsApplied = true
  try {
    let client = Client
    // Rhino selects Integer.valueOf(String) for a JS number and formats it as
    // "12.0". Supply an integer string explicitly, as the validated benchmark did.
    client.options.renderDistance().set(Java.loadClass('java.lang.Integer').valueOf('12'))
    // The installed 6.0 deserializer accepts 0, which removes dy^2 from its
    // metric. This restores cylindrical distance instead of hiding the ground.
    let config = Java.loadClass('com.betterfpsdist.BetterfpsdistMod').config.getCommonConfig()
    config.verticalScaling = 0.0
    config.horizontalScaling = 1.0
    config.affectEntities = false
    client.options.save()
    if (client.level != null) client.levelRenderer.allChanged()
    console.info('[Expedition rendering] renderDistance=12; vertical distance culling disabled')
  } catch (error) {
    console.error('[Expedition rendering] Could not apply defaults: ' + error)
  }
  try {
    let hud = Java.loadClass('xaero.common.HudMod').INSTANCE
    hud.getHudIO().load('module;id=xaerominimap:minimap;x=0;y=0;centered=false;fromRight=true;fromBottom=false;flippedVer=false;flippedHor=false;', false)
    console.info('[Expedition HUD] Minimap anchored to top right')
  } catch (error) {
    console.error('[Expedition HUD] Could not position minimap: ' + error)
  }
  try {
    let extraOptions = Java.loadClass('me.flashyreese.mods.sodiumextra.client.SodiumExtraClientMod').options()
    extraOptions.extraSettings.overlayCorner = Java.loadClass('me.flashyreese.mods.sodiumextra.client.gui.SodiumExtraGameOptions$OverlayCorner').TOP_LEFT
    extraOptions.extraSettings.showFps = true
    extraOptions.extraSettings.showFPSExtended = false
    extraOptions.writeChanges()
    console.info('[Expedition HUD] Simple FPS enabled at top left')
  } catch (error) {
    console.error('[Expedition HUD] Could not enable FPS: ' + error)
  }
})
