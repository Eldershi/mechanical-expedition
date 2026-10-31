// Full restart required. Apply on the logical server, including LAN worlds.
// KubeJS remaps DamageSource.getEntity() to getActual(): the responsible player.
const ExpeditionPeacefulPlayer = Java.loadClass('net.minecraft.world.entity.player.Player')

global.expeditionIsPlayerDamage = (victim, source) => {
  if (!(victim instanceof ExpeditionPeacefulPlayer)) return false
  let attacker = source.getActual()
  return attacker instanceof ExpeditionPeacefulPlayer &&
    !victim.equals(attacker)
}

function expeditionPreventPlayerDamage(event) {
  if (global.expeditionIsPlayerDamage(event.getEntity(), event.getSource()))
    event.setCanceled(true)
}

// Attack catches ordinary hits before effects; later stages also catch mods
// which dispatch damage directly. Self damage and environmental hazards remain.
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingAttackEvent', expeditionPreventPlayerDamage)
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingHurtEvent', expeditionPreventPlayerDamage)
ForgeEvents.onEvent('net.minecraftforge.event.entity.living.LivingDamageEvent', expeditionPreventPlayerDamage)
