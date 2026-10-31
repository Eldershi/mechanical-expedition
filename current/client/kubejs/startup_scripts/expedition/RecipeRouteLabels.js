// Client-side only. Reuses installed JEI + Forge + KubeJS; no extra mod or item NBT.
if (Platform.isClientEnvironment()) {
  let RouteLabelsMinecraft = Java.loadClass('net.minecraft.client.Minecraft')
  let RouteLabelsScreen = Java.loadClass('mezz.jei.gui.recipes.RecipesGui')
  let RouteLabelsEither = Java.loadClass('com.mojang.datafixers.util.Either')
  let routeLabelsModified = null
  let routeLabelsWarned = false
  ForgeEvents.onEvent('net.minecraftforge.client.event.RenderTooltipEvent$GatherComponents', event => {
    try {
      let minecraft = RouteLabelsMinecraft.getInstance()
      let screen = minecraft.screen
      if (!(screen instanceof RouteLabelsScreen)) return
      let window = minecraft.getWindow()
      let mouseX = minecraft.mouseHandler.xpos() * window.getGuiScaledWidth() / window.getScreenWidth()
      let mouseY = minecraft.mouseHandler.ypos() * window.getGuiScaledHeight() / window.getScreenHeight()
      let underMouse = screen.getRecipeLayoutUnderMouse(mouseX, mouseY)
      if (!underMouse.isPresent()) return
      let layout = underMouse.get().getRecipeLayout()
      let slot = layout.getRecipeSlotUnderMouse(mouseX, mouseY)
      if (!slot.isPresent() || String(slot.get().getRole()) !== 'OUTPUT') return
      let idValue = layout.getRecipeCategory().getRegistryName(layout.getRecipe())
      if (idValue == null) return
      let id = String(idValue)
      if (routeLabelsModified == null) {
        routeLabelsModified = {}
        let data = JsonIO.readJson('kubejs/config/expedition-recipe-labels.json')
        if (data == null) return
        data.getAsJsonObject().getAsJsonArray('modified').forEach(value => {
          routeLabelsModified[String(value.getAsString())] = true
        })
      }
      let label = ''
      if (id.startsWith('expedition:selected_native/') || id.startsWith('expedition:pre_steam/') || id === 'expedition:mixing/brass_ingot') {
        label = '§7◇ 原配方'
      } else if (Object.prototype.hasOwnProperty.call(routeLabelsModified, id) || id.indexOf(':kjs/') >= 0 || id.startsWith('kubejs:')) {
        label = '§6◆ 魔改配方'
      }
      if (label !== '') event.getTooltipElements().add(RouteLabelsEither.left(Text.of(label)))
    } catch (error) {
      if (!routeLabelsWarned) {
        routeLabelsWarned = true
        console.warn('[Recipe Route Labels] ' + error)
      }
    }
  })
}
