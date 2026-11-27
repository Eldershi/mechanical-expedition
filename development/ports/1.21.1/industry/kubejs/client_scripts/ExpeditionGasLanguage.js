ClientEvents.lang('zh_cn', event => {
  const gases = {
    'cmi.acetylene': '乙炔',
    'cmi.light_olefin': '轻烯烃',
    'cmi.radon': '氡',
    'expedition.oxygen': '氧气',
    'expedition.nitrogen': '氮气',
    'expedition.hydrogen': '氢气',
    'expedition.ethene': '乙烯',
    'expedition.chlorine': '氯气',
    'expedition.hydrogen_chloride': '氯化氢',
    'expedition.sulfur_dioxide': '二氧化硫',
    'expedition.sulfur_trioxide': '三氧化硫蒸气',
    'expedition.deuterium': '氘气',
    'expedition.tritium': '氚气',
    'expedition.fusion_fuel': '氘氚燃料气'
  }
  Object.entries(gases).forEach(([key, name]) => event.add('gas.' + key, name))
})
