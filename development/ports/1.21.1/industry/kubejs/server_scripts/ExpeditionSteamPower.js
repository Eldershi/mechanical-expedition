ServerEvents.recipes(event => {
  for (const metal of ['bronze', 'cast_iron', 'steel']) {
    event.shaped('steampowered:' + metal + '_steam_engine', ['ABE', 'MCF', 'ABE'], {
      A: '#c:plates/' + metal,
      B: '#c:ingots/' + metal,
      C: '#c:storage_blocks/bronze',
      E: 'create:andesite_alloy',
      F: 'create:shaft',
      M: 'cmi:bronze_mechanism'
    }).id('expedition:factory/steam/' + metal + '_engine')
  }
})
