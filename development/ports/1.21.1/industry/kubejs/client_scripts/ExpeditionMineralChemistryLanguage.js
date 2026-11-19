ClientEvents.lang('zh_cn', event => {
  const fluids = {
    molten_pure_silicon: '熔融高纯硅',
    germanium_solution: '锗溶液',
    entro_peroxide_solution: '过氧化恩特罗溶液',
    delta_unstable_solution: 'Δ 型不稳定源质溶液',
    molten_azure_neodymium: '熔融皓蓝钕',
    molten_scarlet_neodymium: '熔融绯红钕',
    molten_neodymium_mixture: '熔融钕混合物',
    crystal_etching_solution: '水晶蚀刻溶液',
    molten_ionized_entro: '熔融电离恩特罗',
    ionized_entro_solution: '恩特罗电离液',
    molten_silicon_containing_compound: '熔融含硅化合物',
    pure_crystal_source: '纯净晶源',
    liquid_crystal_entro: '液晶态恩特罗',
    liquid_crystal_etrium: '液晶态埃忒恩',
    crystal_entro_solution: '晶态恩特罗溶液'
  }
  for (const name of Object.keys(fluids)) {
    event.add(`fluid_type.cmi.${name}`, fluids[name])
    if (name !== 'molten_pure_silicon') {
      event.add(`block.cmi.${name}`, fluids[name])
      event.add(`item.cmi.${name}_bucket`, fluids[name] + '桶')
    }
  }
  event.add('gas.cmi.helium_3', '氦-3')
  event.add('gas.cmi.nuke_waste', '核废气')
  event.add('gas.cmi.radioactive_mixture', '放射性混合气体')
  event.add('chemical.cmi.germanium_precursor', '含锗化学品')
  event.add('chemical.cmi.entro_peroxide', '过氧化恩特罗化学品')
  event.add('chemical.cmi.chaotic_void', '混沌虚空')
  event.add('chemical.cmi.infuse_osmium', '灌注锇')
  event.add('chemical.cmi.etrium', '埃忒恩')
  const deposits = { aluminum: '铝', platinum: '铂', vanadium: '钒', oil_shale: '油页岩', cheese: '奶酪', coal: '煤' }
  for (const name of Object.keys(deposits)) {
    event.add(`block.cmi.${name}_deposit_block`, `${deposits[name]}矿床`)
  }
  event.add('block.cmi.nether_vanadium_ore', '下界钒矿石')
  event.add('block.cmi.moon_platinum_ore', '月球铂矿石')
  event.add('block.cmi.oil_shale', '油页岩')
  event.add('item.cmi.vanadium_dust', '钒粉')
  event.add('expedition.catalyst.vanadium_overclock.name', '钒矿熔岩超频')
  event.add('expedition.catalyst.vanadium_overclock.description', '每批消耗 20 mB 熔岩。')
})

ClientEvents.lang('en_us', event => {
  event.add('gas.cmi.helium_3', 'Helium-3')
  event.add('gas.cmi.nuke_waste', 'Nuclear Waste Gas')
  event.add('gas.cmi.radioactive_mixture', 'Radioactive Gas Mixture')
  event.add('expedition.catalyst.vanadium_overclock.name', 'Vanadium Lava Overclock')
  event.add('expedition.catalyst.vanadium_overclock.description', 'Consumes 20 mB of lava per batch.')
  event.add('chemical.cmi.germanium_precursor', 'Germanium Precursor')
  event.add('chemical.cmi.entro_peroxide', 'Entro Peroxide')
})
