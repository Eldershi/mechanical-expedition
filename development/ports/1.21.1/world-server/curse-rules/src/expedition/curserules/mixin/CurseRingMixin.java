package expedition.curserules.mixin;

import auviotre.enigmatic.legacy.contents.item.rings.CursedRing;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import top.theillusivec4.curios.api.SlotContext;

@Mixin(value = CursedRing.class, remap = false)
abstract class CurseRingMixin {
    // The rest of curioTick handles proximity anger and Enderman attraction.
    @Inject(method = "curioTick", at = @At(value = "INVOKE",
        target = "Lnet/neoforged/neoforge/common/ModConfigSpec$DoubleValue;getAsDouble()D"), cancellable = true)
    private void expedition$skipNeutralAggression(SlotContext slot, ItemStack stack, CallbackInfo callback) {
        callback.cancel();
    }

    @Inject(method = "canSleepWithCurse", at = @At("HEAD"), cancellable = true)
    private static void expedition$allowSleep(Player player, CallbackInfoReturnable<Boolean> callback) {
        callback.setReturnValue(true);
    }
}
