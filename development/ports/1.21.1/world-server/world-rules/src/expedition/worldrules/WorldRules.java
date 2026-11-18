package expedition.worldrules;

import java.util.Set;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.MobSpawnType;
import net.neoforged.fml.ModList;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.EntityInvulnerabilityCheckEvent;
import net.neoforged.neoforge.event.entity.living.FinalizeSpawnEvent;
import net.neoforged.neoforge.event.entity.living.LivingDamageEvent;
import net.neoforged.neoforge.event.entity.living.LivingIncomingDamageEvent;

@Mod("expedition_world_rules")
public final class WorldRules {
    private static final Set<ResourceLocation> BLOCKED_NATURAL_SPAWNS = Set.of(
        ResourceLocation.parse("born_in_chaos_v1:maggot"),
        ResourceLocation.parse("born_in_chaos_v1:corpse_fly")
    );

    public WorldRules() {
        NeoForge.EVENT_BUS.addListener(WorldRules::finalizeSpawn);
        NeoForge.EVENT_BUS.addListener(WorldRules::checkInvulnerability);
        NeoForge.EVENT_BUS.addListener(WorldRules::checkIncomingDamage);
        NeoForge.EVENT_BUS.addListener(WorldRules::checkFinalDamage);
        if (ModList.get().isLoaded("biomesoplenty")) {
            new ShortGrass().register();
        }
        if (ModList.get().isLoaded("neoecoae") && ModList.get().isLoaded("ad_astra")) {
            Cryotheum.register();
        }
    }

    private static void finalizeSpawn(FinalizeSpawnEvent event) {
        MobSpawnType reason = event.getSpawnType();
        if ((reason == MobSpawnType.NATURAL || reason == MobSpawnType.CHUNK_GENERATION)
                && BLOCKED_NATURAL_SPAWNS.contains(BuiltInRegistries.ENTITY_TYPE.getKey(event.getEntity().getType()))) {
            event.setSpawnCancelled(true);
        }
    }

    private static boolean otherPlayerDamage(Entity victim, DamageSource source) {
        return victim instanceof ServerPlayer && source.getEntity() instanceof ServerPlayer attacker
            && !victim.equals(attacker);
    }

    private static void checkInvulnerability(EntityInvulnerabilityCheckEvent event) {
        if (otherPlayerDamage(event.getEntity(), event.getSource())) {
            event.setInvulnerable(true);
        }
    }

    private static void checkIncomingDamage(LivingIncomingDamageEvent event) {
        if (otherPlayerDamage(event.getEntity(), event.getSource())) {
            event.setCanceled(true);
        }
    }

    private static void checkFinalDamage(LivingDamageEvent.Pre event) {
        if (otherPlayerDamage(event.getEntity(), event.getSource())) {
            event.setNewDamage(0);
        }
    }
}
