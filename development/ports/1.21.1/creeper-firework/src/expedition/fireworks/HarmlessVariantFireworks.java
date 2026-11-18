package expedition.fireworks;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.neoforged.neoforge.network.PacketDistributor;
import plus.dragons.creeperfirework.Configuration;
import plus.dragons.creeperfirework.network.Payload;

public final class HarmlessVariantFireworks {
    private HarmlessVariantFireworks() {}

    /** Reuse the upstream visual payload without causing an explosion or spawning a projectile. */
    public static boolean convert(Entity entity, boolean charged) {
        if (!(entity.level() instanceof ServerLevel level)
                || !Configuration.isCreeperExplodeIntoFirework()
                || level.random.nextDouble() >= Configuration.becomeFireworkChance()) {
            return false;
        }
        PacketDistributor.sendToPlayersNear(level, null, entity.getX(), entity.getY(), entity.getZ(),
                192, new Payload(entity.blockPosition(), charged));
        entity.discard();
        return true;
    }
}
