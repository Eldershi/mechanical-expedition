const ExpeditionItemEnergy = Java.loadClass('net.neoforged.neoforge.capabilities.Capabilities$EnergyStorage').ITEM
const ExpeditionRadarItemTrait = Java.loadClass('com.lowdragmc.mbd2.common.trait.item.ItemSlotCapabilityTrait')
const ExpeditionRadarEnergyTrait = Java.loadClass('com.lowdragmc.mbd2.common.trait.forgeenergy.ForgeEnergyCapabilityTrait')

function expeditionTransferRadarEnergy(stack, receiver) {
  if (stack.isEmpty()) return
  const source = stack.getCapability(ExpeditionItemEnergy)
  if (source == null) return
  const accepted = receiver.receiveEnergy(1000, true)
  if (accepted <= 0) return
  const extracted = source.extractEnergy(accepted, false)
  if (extracted > 0) receiver.receiveEnergy(extracted, false)
}

MBDMachineEvents.onTick('cmi:radar_antenna', callback => {
  const machine = callback.getEvent().getMachine()
  const energySlot = machine.getTraitByName(ExpeditionRadarItemTrait, 'item_energy')
  const energy = machine.getTraitByName(ExpeditionRadarEnergyTrait, 'forge_energy_storage')
  if (energySlot != null && energy != null) {
    expeditionTransferRadarEnergy(energySlot.storage.getStackInSlot(0), energy.storage)
  }
})
