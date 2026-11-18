ServerEvents.recipes(event => {
  event.custom({
    type: 'create:mixing',
    heat_requirement: 'heated',
    ingredients: [{ type: 'neoforge:tag', tag: 'minecraft:water', amount: 1000 }],
    results: [{ id: 'steam_letters:steam', amount: 1000 }]
  }).id('expedition:steam_mixing/steam')

  event.custom({
    type: 'create:mixing',
    heat_requirement: 'superheated',
    ingredients: [{ type: 'neoforge:tag', tag: 'c:steam', amount: 1000 }],
    results: [{ id: 'steam_letters:superheated_steam', amount: 1000 }]
  }).id('expedition:steam_mixing/superheated_steam')
})
