ClientEvents.lang('zh_cn', event => {
  const fluids = {
    conditioned_crude_oil: '预处理原油',
    bitumen: '液态沥青',
    sulfric_diesel: '含硫柴油',
    kerosene: '煤油',
    naphtha: '石脑油',
    cracked_gasoline: '裂化汽油',
    benzene: '苯',
    light_olefin: '轻烯烃',
    phenol: '苯酚'
  }
  Object.keys(fluids).forEach(key => {
    event.add(`fluid.cmi.${key}`, fluids[key])
    event.add(`block.cmi.${key}`, fluids[key])
    event.add(`item.cmi.${key}_bucket`, `${fluids[key]}桶`)
  })
})
