const CreateInventoryRegistryKeys = Java.loadClass('net.minecraft.core.registries.Registries')

ServerEvents.loaded(event => {
  const registries = event.server.registryAccess()
  const ids = key => {
    const values = []
    registries.registryOrThrow(key).keySet().forEach(id => values.push(String(id)))
    return values.sort()
  }
  JsonIO.write('kubejs/exported/create-inventory-target-registry.json', {
    items: ids(CreateInventoryRegistryKeys.ITEM),
    enchantments: ids(CreateInventoryRegistryKeys.ENCHANTMENT)
  })
})
