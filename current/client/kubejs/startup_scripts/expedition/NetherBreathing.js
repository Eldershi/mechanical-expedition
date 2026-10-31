// Full client/server restart required. This runs after CMI's static Forge subscribers register.
// CMI Core 1.3 hard-codes Nether air loss in this class, with no configuration switch.
// Unregister that exact subscriber instead of cancelling drowning or space-oxygen damage.
const ExpeditionNetherForge = Java.loadClass('net.minecraftforge.common.MinecraftForge')
const ExpeditionNetherBreathingHandler = Java.loadClass('dev.celestiacraft.cmi.event.NetherBreathingHandler')

StartupEvents.postInit(() => {
  ExpeditionNetherForge.EVENT_BUS.unregister(ExpeditionNetherBreathingHandler)
  console.info('[Expedition Nether Breathing] Disabled CMI Nether breathing restriction; normal fluid and space oxygen rules remain.')
})

if (Platform.isClientEnvironment()) {
  // This CMI overlay advertises Nether backtank air even after its requirement is disabled.
  ForgeEvents.onEvent('net.minecraftforge.client.event.RenderGuiOverlayEvent$Pre', event => {
    if (String(event.getOverlay().id()) === 'cmi:cmi_nether_backtank_air') event.setCanceled(true)
  })
}
