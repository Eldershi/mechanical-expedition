ClientEvents.lang('zh_cn', event => {
  const mechanisms = {
    andesite: '安山', copper: '铜质', bronze: '青铜', iron: '铁质',
    nether: '下界', ender: '末影', railway: '铁路', coil: '线圈',
    light_engineering: '轻型工程', heavy_engineering: '重型工程',
    smart: '智能', photosensitive: '感光', basic_mekanism: '基础通用',
    advanced_mekanism: '高级通用', elite_mekanism: '精英通用',
    ultimate_mekanism: '终极通用', computing: '计算', air_tight: '气密',
    aeronautic: '航空', nuclear: '核', astronautic: '宇航',
    antimatter: '反物质', creative: '创造'
  }
  const parts = {
    basic: '基础', mechanical: '机械', engineering: '工程', flux: '通量',
    magical: '魔力', quantum: '量子', mekanism: '通用', final: '终章', space: '太空'
  }
  const add = (id, name) => {
    if (Item.exists('cmi:' + id)) event.add('item.cmi.' + id, name)
  }
  Object.entries(mechanisms).forEach(([id, name]) => {
    add(id + '_mechanism', name + '构件')
    add('incomplete_' + id + '_mechanism', name + '构件（半成品）')
    add(id + '_mechanism_basement', name + '构件底座')
    add(id + '_mechanism_augment', name + '构件组件')
  })
  Object.entries(parts).forEach(([id, name]) => {
    add(id + '_mechanism_part', name + '构件零件')
  })
  add('mechanism_mold', '构件模具')
})
