ClientEvents.lang('zh_cn', event => {
  event.add('block.cmi.osmium_tile', '锇砖瓦')
  const fluids = {
    cracked_diesel: '裂化柴油',
    light_aldehyde: '轻醛烃',
    acetylene: '乙炔',
    vinyl_alcohol: '乙烯醇',
    polyvinyl_alcohol: '聚乙烯醇',
    structural_plastic: '结构塑胶'
  }
  Object.keys(fluids).forEach(key => {
    event.add(`fluid.cmi.${key}`, fluids[key])
    event.add(`block.cmi.${key}`, fluids[key])
    event.add(`item.cmi.${key}_bucket`, `${fluids[key]}桶`)
  })
})
