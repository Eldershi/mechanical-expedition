package expedition.nebula;

import modernmods.modernfoundry.library.modifiers.ModifierId;
import modernmods.modernfoundry.library.modifiers.modules.ModifierModule;
import modernmods.modernfoundry.library.tools.definition.module.aoe.AreaOfEffectIterator;
import modernmods.modernfoundry.library.tools.item.IModifiable;
import modernmods.modernfoundry.library.tools.nbt.ToolStack;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.effect.MobEffect;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.item.Item;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.player.CriticalHitEvent;
import net.neoforged.neoforge.registries.DeferredRegister;

@Mod("expedition_nebula_tinker_compat")
public final class NebulaTinkerCompat {
    private static final DeferredRegister.Items ITEMS = DeferredRegister.createItems("nebula_tinker");
    private static final DeferredRegister.Items MATERIALS = DeferredRegister.createItems("expedition");
    private static final ModifierId ABUSER = new ModifierId("nebula_tinker", "abuser");
    private static final ModifierId CLOCKWORK = new ModifierId("nebula_tinker", "clockwork");
    private static final ResourceKey<MobEffect> BLEEDING = ResourceKey.create(
            Registries.MOB_EFFECT, ResourceLocation.fromNamespaceAndPath("modernfoundry", "bleeding"));

    public NebulaTinkerCompat(IEventBus modBus) {
        ITEMS.registerSimpleItem("spider_fang", new Item.Properties());
        ITEMS.register(modBus);
        MATERIALS.registerSimpleItem("clockwork_brass_ingot", new Item.Properties());
        MATERIALS.register(modBus);
        ModifierModule.LOADER.register(id("shadow_damage"), ShadowDamageModule.LOADER);
        AreaOfEffectIterator.register(id("connected_vein"), ConnectedVeinIterator.LOADER);
        NeoForge.EVENT_BUS.addListener(NebulaTinkerCompat::onCriticalHit);
    }

    private static ResourceLocation id(String path) {
        return ResourceLocation.fromNamespaceAndPath("nebula_tinker", path);
    }

    private static void onCriticalHit(CriticalHitEvent event) {
        var player = event.getEntity();
        if (player.level().isClientSide() || !(event.getTarget() instanceof LivingEntity target)) {
            return;
        }
        var stack = player.getMainHandItem();
        if (!(stack.getItem() instanceof IModifiable)) {
            return;
        }
        var tool = ToolStack.from(stack);
        if (tool.isBroken()) {
            return;
        }

        var effects = target.registryAccess().registryOrThrow(Registries.MOB_EFFECT);
        if (tool.getModifierLevel(ABUSER) > 0 && (target.hasEffect(MobEffects.POISON)
                || target.hasEffect(MobEffects.WITHER)
                || effects.getHolder(BLEEDING).filter(target::hasEffect).isPresent())) {
            event.setCriticalHit(true);
            event.setDamageMultiplier(1.5F);
            event.setDisableSweep(true);
        }

        var speed = player.getEffect(MobEffects.MOVEMENT_SPEED);
        if (tool.getModifierLevel(CLOCKWORK) > 0 && speed != null) {
            int level = speed.getAmplifier() + 1;
            boolean alreadyCritical = event.isCriticalHit();
            if (alreadyCritical || player.getRandom().nextFloat() < 0.05F * level) {
                float base = alreadyCritical ? event.getDamageMultiplier() : 1.5F;
                event.setCriticalHit(true);
                event.setDamageMultiplier(base + 0.10F * level);
                event.setDisableSweep(true);
            }
        }
    }
}
