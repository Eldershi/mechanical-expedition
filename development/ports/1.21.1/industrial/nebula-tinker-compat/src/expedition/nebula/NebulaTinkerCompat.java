package expedition.nebula;

import modernmods.modernfoundry.library.modifiers.ModifierId;
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
    private static final ModifierId ABUSER = new ModifierId("nebula_tinker", "abuser");
    private static final ResourceKey<MobEffect> BLEEDING = ResourceKey.create(
            Registries.MOB_EFFECT, ResourceLocation.fromNamespaceAndPath("modernfoundry", "bleeding"));

    public NebulaTinkerCompat(IEventBus modBus) {
        ITEMS.registerSimpleItem("spider_fang", new Item.Properties());
        ITEMS.register(modBus);
        NeoForge.EVENT_BUS.addListener(NebulaTinkerCompat::onCriticalHit);
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
        if (tool.isBroken() || tool.getModifierLevel(ABUSER) == 0) {
            return;
        }

        var effects = target.registryAccess().registryOrThrow(Registries.MOB_EFFECT);
        if (target.hasEffect(MobEffects.POISON) || target.hasEffect(MobEffects.WITHER)
                || effects.getHolder(BLEEDING).filter(target::hasEffect).isPresent()) {
            event.setCriticalHit(true);
            event.setDamageMultiplier(1.5F);
            event.setDisableSweep(true);
        }
    }
}
