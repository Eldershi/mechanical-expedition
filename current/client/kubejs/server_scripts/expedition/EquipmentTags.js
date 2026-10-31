// priority: -200
// Apply after the upstream tags; retain unrelated accessories from every mod.
ServerEvents.tags('item', event => {
  event.get('curios:belt').add('#curios:waist')
  event.get('curios:ring').add('#curios:rings').add('#aether:accessories_rings')
  event.get('curios:hands').add('#aether:accessories_gloves')
  event.get('curios:necklace').add('#aether:accessories_pendants')
  event.get('curios:back').add('#aether:accessories_capes')
  event.get('curios:curio').add('#aether:accessories_miscellaneous')
  ;["sophisticatedbackpacks:backpack", "sophisticatedbackpacks:copper_backpack", "sophisticatedbackpacks:iron_backpack", "sophisticatedbackpacks:gold_backpack", "sophisticatedbackpacks:diamond_backpack", "sophisticatedbackpacks:netherite_backpack"].forEach(id => event.get('curios:back').remove(id))
  // Aether's official Curios pack defaults to charm/body; use the requested mapping.
  event.get('curios:charm').remove('#aether:accessories_miscellaneous')
  ;['aether:golden_feather', 'aether:regeneration_stone', 'aether:iron_bubble']
    .forEach(id => event.get('curios:charm').remove(id))
  event.get('curios:body').remove('#aether:accessories_shields').remove('aether:shield_of_repulsion')
})
