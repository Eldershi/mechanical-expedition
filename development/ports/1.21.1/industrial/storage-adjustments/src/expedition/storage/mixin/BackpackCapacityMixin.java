package expedition.storage.mixin;

import net.minecraft.world.item.ItemStack;
import net.p3pp3rf1y.sophisticatedcore.api.IStorageWrapper;
import net.p3pp3rf1y.sophisticatedcore.common.gui.UpgradeSlotChangeResult;
import net.p3pp3rf1y.sophisticatedcore.upgrades.stack.StackUpgradeItem;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = StackUpgradeItem.class, remap = false)
public abstract class BackpackCapacityMixin {
    @Shadow @Final private double stackSizeMultiplier;

    @Shadow
    private static int getInventorySlotLimit(double multiplier) {
        throw new AssertionError();
    }

    @Shadow
    static UpgradeSlotChangeResult isMultiplierHighEnough(
            IStorageWrapper storage, double requested, int slot) {
        throw new AssertionError();
    }

    @Inject(method = "getInventorySlotLimit(Lnet/p3pp3rf1y/sophisticatedcore/api/IStorageWrapper;D)I",
            at = @At("HEAD"), cancellable = true)
    private static void expedition$additive(
            IStorageWrapper storage, double excluded, CallbackInfoReturnable<Integer> result) {
        result.setReturnValue(getInventorySlotLimit(expedition$multiplier(storage, excluded, 0)));
    }

    @Redirect(method = "checkExtraInsertConditions", at = @At(value = "INVOKE", target =
            "Lnet/p3pp3rf1y/sophisticatedcore/upgrades/stack/StackUpgradeItem;isMultiplierHighEnough("
            + "Lnet/p3pp3rf1y/sophisticatedcore/api/IStorageWrapper;DI)"
            + "Lnet/p3pp3rf1y/sophisticatedcore/common/gui/UpgradeSlotChangeResult;"))
    private UpgradeSlotChangeResult expedition$checkInsertion(
            IStorageWrapper storage, double oldForecast, int slot) {
        return isMultiplierHighEnough(storage, expedition$multiplier(storage, -1, stackSizeMultiplier), slot);
    }

    @Redirect(method = "canSwapUpgradeFor", at = @At(value = "INVOKE", target =
            "Lnet/p3pp3rf1y/sophisticatedcore/upgrades/stack/StackUpgradeItem;isMultiplierHighEnough("
            + "Lnet/p3pp3rf1y/sophisticatedcore/api/IStorageWrapper;DI)"
            + "Lnet/p3pp3rf1y/sophisticatedcore/common/gui/UpgradeSlotChangeResult;"))
    private UpgradeSlotChangeResult expedition$checkSwap(
            IStorageWrapper storage, double oldForecast, int slot,
            ItemStack replacement, int upgradeSlot, IStorageWrapper argumentStorage, boolean fromContainer) {
        StackUpgradeItem upgrade = (StackUpgradeItem) replacement.getItem();
        double multiplier = expedition$multiplier(storage, stackSizeMultiplier, upgrade.getStackSizeMultiplier());
        return isMultiplierHighEnough(storage, multiplier, slot);
    }

    @Unique
    private static double expedition$multiplier(IStorageWrapper storage, double excluded, double added) {
        double sum = added;
        boolean skipNextMatch = excluded > 0;
        for (var wrapper : storage.getUpgradeHandler().getTypeWrappers(StackUpgradeItem.TYPE)) {
            double installed = wrapper.getStackSizeMultiplier();
            if (skipNextMatch && Double.compare(installed, excluded) == 0) {
                skipNextMatch = false;
            } else {
                sum += installed;
            }
        }
        return sum > 0 ? sum : storage.getBaseStackSizeMultiplier();
    }
}
