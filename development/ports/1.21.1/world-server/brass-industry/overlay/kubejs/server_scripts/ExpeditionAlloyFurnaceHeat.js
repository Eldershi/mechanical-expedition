const alloyFurnaceEnergyTrait = Java.loadClass('com.lowdragmc.mbd2.common.trait.forgeenergy.ForgeEnergyCapabilityTrait')

MBDMachineEvents.onTick('expedition_industry:alloy_furnace', callback => {
  const machine = callback.getEvent().getMachine()
  if (machine.getOffsetTimer() % 4 !== 0) return
  const energy = machine.getTraitByName(alloyFurnaceEnergyTrait, 'forge_energy_storage').getStorage()
  const hot = machine.isFormedValid() && energy.getEnergyStored() > 0
  const data = machine.getCustomData()
  if (data.getBoolean('alloyHot') === hot) return
  const update = data.copy()
  update.putBoolean('alloyHot', hot)
  machine.setCustomData(update)
})
