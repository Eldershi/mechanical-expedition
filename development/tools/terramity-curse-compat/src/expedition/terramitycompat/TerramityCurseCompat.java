package expedition.terramitycompat;

import com.aizistral.enigmaticlegacy.handlers.SuperpositionHandler;
import com.aizistral.enigmaticlegacy.items.CursedRing;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.*;
import net.minecraft.world.entity.monster.Monster;
import net.minecraft.world.entity.boss.enderdragon.EnderDragon;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.projectile.Projectile;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.extensions.IForgeEntity;
import net.minecraftforge.event.entity.living.MobEffectEvent;
import net.minecraftforge.event.entity.living.MobSpawnEvent;
import net.minecraftforge.eventbus.api.Event;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.ForgeRegistries;
import java.util.Set;

/** Retain the applier of shadowflame so normal combat rules also govern its damage. */
@Mod("expedition_terramity_curse_compat")
public final class TerramityCurseCompat {
    private static final String OWNER="expedition_shadowflame_owner";
    private static final String PENALTY="expedition_shadowflame_penalty";
    private static final ResourceLocation EFFECT=new ResourceLocation("terramity", "nyxium_fire");
    private static final Set<String> NO_NATURAL=Set.of("blue_fairy","green_fairy","pink_fairy","cave_gnome","royal_gnome");
    private static final ThreadLocal<Boolean> DOT=ThreadLocal.withInitial(()->false);

    public TerramityCurseCompat() {
        MinecraftForge.EVENT_BUS.addListener(this::added);
        MinecraftForge.EVENT_BUS.addListener(this::expired);
        MinecraftForge.EVENT_BUS.addListener(this::removed);
        MinecraftForge.EVENT_BUS.addListener(this::spawn);
    }
    private void added(MobEffectEvent.Added event) {
        if (event.getEntity().m_9236_().f_46443_ || !EFFECT.equals(ForgeRegistries.MOB_EFFECTS.getKey(event.getEffectInstance().m_19544_()))) return;
        // Damage reactions must not overwrite the original application with an anonymous refresh.
        if (DOT.get()) return;
        Entity source=event.getEffectSource();
        if(source instanceof Projectile projectile) source=projectile.m_19749_();
        CompoundTag data=((IForgeEntity)event.getEntity()).getPersistentData();
        if(source instanceof Player player) {
            data.m_128362_(OWNER,player.m_20148_());
            float penalty=SuperpositionHandler.isTheCursedOne(player) ? CursedRing.monsterDamageDebuff.getValue().asModifierInverted() : 1.0F;
            data.m_128350_(PENALTY,penalty);
        } else clear(event.getEntity());
    }
    private static void clear(LivingEntity target) {
        ((IForgeEntity)target).getPersistentData().m_128473_(OWNER);((IForgeEntity)target).getPersistentData().m_128473_(PENALTY);
    }
    private void expired(MobEffectEvent.Expired event) {
        if(event.getEffectInstance()!=null && EFFECT.equals(ForgeRegistries.MOB_EFFECTS.getKey(event.getEffectInstance().m_19544_()))) clear(event.getEntity());
    }
    private void removed(MobEffectEvent.Remove event) {
        if(EFFECT.equals(ForgeRegistries.MOB_EFFECTS.getKey(event.getEffect()))) clear(event.getEntity());
    }
    private void spawn(MobSpawnEvent.SpawnPlacementCheck event) {
        ResourceLocation id=ForgeRegistries.ENTITY_TYPES.getKey(event.getEntityType());
        if(id!=null && id.m_135827_().equals("terramity") && NO_NATURAL.contains(id.m_135815_()) &&
           (event.getSpawnType()==MobSpawnType.NATURAL || event.getSpawnType()==MobSpawnType.CHUNK_GENERATION)) event.setResult(Event.Result.DENY);
    }
    public static boolean hurt(Entity target, DamageSource original, float amount) {
        CompoundTag data=((IForgeEntity)target).getPersistentData();
        Entity owner=null;
        if(data.m_128403_(OWNER) && target.m_20194_()!=null) owner=target.m_20194_().m_6846_().m_11259_(data.m_128342_(OWNER));
        DamageSource source=original;
        if(owner!=null) {
            // No direct melee entity: changing held weapons cannot invoke a melee-only curse exemption.
            source=new DamageSource(original.m_269150_(),null,owner);
        } else if(data.m_128403_(OWNER) && (target instanceof Monster || target instanceof EnderDragon)) {
            // Keep the last confirmed curse reduction when the applier is offline or dead.
            amount*=data.m_128457_(PENALTY);
        }
        boolean previous=DOT.get();DOT.set(true);
        try { return target.m_6469_(source,amount); }
        finally { DOT.set(previous); }
    }
    public static boolean applyingDamage() {return DOT.get();}
}
