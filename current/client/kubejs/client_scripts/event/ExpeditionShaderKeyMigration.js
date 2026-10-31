// One-time migration for existing clients; future manual key changes are kept.
let expeditionShaderKeyMigrationChecked = false
ClientEvents.tick(event => {
  if (expeditionShaderKeyMigrationChecked) return
  expeditionShaderKeyMigrationChecked = true
  try {
    let path = 'config/expedition-keybind-migrations.json'
    let migration = 'shaderReloadAwayFromR_v1'
    let state = JsonIO.read(path) || {}
    if (state[migration]) return

    let mappings = Client.options.keyMappings
    let shader = null
    let occupied = {}
    for (let i = 0; i < mappings.length; i++) {
      let mapping = mappings[i]
      if (String(mapping.getName()) === 'iris.keybind.reload') shader = mapping
      else occupied[String(mapping.getKey().getName())] = true
    }

    let result = {status: 'missing_shader_binding'}
    if (shader != null) {
      let current = String(shader.getKey().getName())
      let modifier = String(shader.getKeyModifier().name())
      result = {status: 'kept_custom_binding', key: current, modifier: modifier}
      // Preserve explicitly modified shortcuts such as Shift+R.
      if (current === 'key.keyboard.r' && modifier === 'NONE') {
        let candidates = ['key.keyboard.f9', 'key.keyboard.f6']
        let selected = null
        for (let i = 0; i < candidates.length; i++) {
          if (!occupied[candidates[i]]) {
            selected = candidates[i]
            break
          }
        }
        if (selected != null) {
          let InputConstants = Java.loadClass('com.mojang.blaze3d.platform.InputConstants')
          shader.setKey(InputConstants.getKey(selected))
          Java.loadClass('net.minecraft.client.KeyMapping').resetMapping()
          Client.options.save()
          result = {status: 'migrated', from: current, key: selected}
          console.info('[Expedition keybinds] Shader reload moved from R to ' + selected)
        } else {
          result = {status: 'kept_no_free_key', key: current}
          console.warn('[Expedition keybinds] F9 and F6 are occupied; shader reload kept on R. Set it manually in Controls.')
        }
      } else {
        console.info('[Expedition keybinds] Shader reload personal binding kept: ' + modifier + ' + ' + current)
      }
    } else {
      console.info('[Expedition keybinds] Shader reload binding unavailable; no keys changed')
    }
    state[migration] = result
    JsonIO.write(path, state)
  } catch (error) {
    console.error('[Expedition keybinds] Could not migrate shader reload: ' + error)
  }
})
