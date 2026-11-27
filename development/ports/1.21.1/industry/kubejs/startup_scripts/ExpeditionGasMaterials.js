StartupEvents.registry('createcraftedbeginning:gas', event => {
  const gases = {
    'cmi:acetylene': ['Acetylene', 0xDDD5B0],
    'cmi:light_olefin': ['Light Olefins', 0x6FEAFF],
    'cmi:radon': ['Radon', 0x7CAA68],
    'expedition:oxygen': ['Oxygen', 0x76B9ED],
    'expedition:nitrogen': ['Nitrogen', 0x9B9FD4],
    'expedition:hydrogen': ['Hydrogen', 0xE2EBF6],
    'expedition:ethene': ['Ethene', 0xE7BE78],
    'expedition:chlorine': ['Chlorine', 0xA5BA4F],
    'expedition:hydrogen_chloride': ['Hydrogen Chloride', 0xD8EAC9],
    'expedition:sulfur_dioxide': ['Sulfur Dioxide', 0xE2D384],
    'expedition:sulfur_trioxide': ['Sulfur Trioxide Vapor', 0xE2E7CF],
    'expedition:deuterium': ['Deuterium', 0x79BCCC],
    'expedition:tritium': ['Tritium', 0x93C592],
    'expedition:fusion_fuel': ['Deuterium–Tritium Fuel', 0x9ABFC0]
  }
  Object.entries(gases).forEach(([id, entry]) => {
    event.create(id).displayName(entry[0]).defaultTexture().tint(entry[1]).usableInEquipment(false)
  })
})
