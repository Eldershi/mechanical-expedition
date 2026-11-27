const ExpeditionSampleBalloons = Java.loadClass('net.ty.createcraftedbeginning.content.airtights.balloon.BalloonItem')
const ExpeditionSampleCanisters = Java.loadClass('net.ty.createcraftedbeginning.api.canister.CanisterCapabilities')

const expeditionGasSamples = {
  '7F4410D119628533': 'cmi:acetylene',
  '5B9DB50FA362B833': 'cmi:light_olefin',
  '7A0344280C9F2302': 'cmi:light_olefin',
  '3C7931161B871AAD': 'cmi:light_olefin',
  '36AF065D8673593B': 'cmi:light_olefin'
}

Object.entries(expeditionGasSamples).forEach(([id, gas]) => {
  const matches = stack => !stack.isEmpty() && Number(stack.getAmount()) >= 50 && String(stack.getGasType()) === gas
  const contains = item => {
    if (item.isEmpty()) return false
    if (ExpeditionSampleBalloons.isBalloon(item)) return matches(ExpeditionSampleBalloons.getGas(item))
    const canister = item.getCapability(ExpeditionSampleCanisters.ITEM)
    if (canister == null) return false
    for (let tank = 0; tank < canister.getTanks(); tank++) {
      if (matches(canister.getGasInTank(tank))) return true
    }
    return false
  }
  FTBQuestsEvents.customTask(id, event => {
    event.setCheckTimer(20)
    event.setCheck((data, player) => {
      const inventory = player.getInventory()
      for (let slot = 0; slot < inventory.getContainerSize(); slot++) {
        if (contains(inventory.getItem(slot))) {
          data.setProgress(1)
          return
        }
      }
    })
  })
})
