package expedition.fireworks;

import net.minecraft.world.entity.monster.Creeper;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.server.level.ServerPlayer;
import net.minecraftforge.network.PacketDistributor;
import plus.dragons.creeperfirework.Configuration;
import plus.dragons.creeperfirework.FireworkEffect;
import plus.dragons.creeperfirework.forge.network.Networking;
import plus.dragons.creeperfirework.forge.network.Packet;

/** Shares the installed Creeper Firework packet with variants that bypass vanilla explodeCreeper. */
public final class HarmlessVariantFireworks {
    private HarmlessVariantFireworks() {}

    public static boolean convert(Creeper creeper) {
        if (!shouldConvert(creeper)) return false;
        // This pack deliberately uses harmless fireworks. Cancel the whole custom
        // explosion, including Overhaul's potion clouds and Sulfur's suit drain.
        FireworkEffect.create(creeper);
        creeper.m_146870_();
        return true;
    }

    public static boolean convert(Entity entity, boolean charged) {
        if (!shouldConvert(entity)) return false;
        // The installed upstream packet contains only a position and charged flag;
        // non-vanilla creeper mobs can safely share its exact rendering effect.
        for (Player nearby : entity.m_9236_().m_6907_()) {
            if (nearby instanceof ServerPlayer player
                    && nearby.m_20183_().m_123314_(entity.m_20183_(), 192.0)) {
                Networking.INSTANCE.send(PacketDistributor.PLAYER.with(() -> player),
                        new Packet(entity.m_20183_(), charged));
            }
        }
        entity.m_146870_();
        return true;
    }

    private static boolean shouldConvert(Entity entity) {
        return !entity.m_9236_().m_5776_()
                && Configuration.isCreeperExplodeIntoFirework()
                && Math.random() < Configuration.becomeFireworkChance();
    }
}
