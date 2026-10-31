// CSA fluid IDs remain registered; Steam Letters handles their boiler input.
ServerEvents.tags("fluid", event => {
    // The old high-temperature steam used the same level 18 as superheated steam.
    event.get("forge:superheated_steam").add("#forge:high_temperature_steam")
})
