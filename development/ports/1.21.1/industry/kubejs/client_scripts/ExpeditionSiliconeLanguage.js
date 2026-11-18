ClientEvents.lang('zh_cn', event => {
  const fluids = {
    vinegar: '醋',
    vinegar_acid: '醋酸',
    light_silicone_ether: '轻硅醚',
    polysilicone_ether: '聚硅醚',
    silicon_rubber: '液态硅橡胶'
  }
  Object.keys(fluids).forEach(key => {
    event.add(`fluid.cmi.${key}`, fluids[key])
    event.add(`block.cmi.${key}`, fluids[key])
    event.add(`item.cmi.${key}_bucket`, `${fluids[key]}桶`)
  })
})
