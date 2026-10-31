// Expedition: retain saved materials and machine registry identities.
StartupEvents.registry("mekanism:gas", event => {
  event.create("cmi:nuke_waste").color(0x4F412A)
  event.create("cmi:spent_nuke_waste").color(0x262015)
})
StartupEvents.registry("item", event => {
  event.create("cmi:basalt_general_component")
    .texture("cmi:item/component/basalz_cell")
    .tag("cmi:general_components")
})
StartupEvents.registry("block", event => {
  event.create("cmi:bronze_solar_boiler", "steam_letters:solar")
    .material("steam_letters:bronze").production(19).capacity(4000)
  event.create("cmi:bronze_fluid_burner", "steam_letters:fluid_burner")
    .material("steam_letters:bronze")
})
