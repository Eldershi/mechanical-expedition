package expedition.storage.mixin;

import java.util.function.Supplier;

import com.buuz135.functionalstorage.item.component.SizeProvider;
import net.minecraft.core.component.DataComponentType;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.items.IItemHandler;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = SizeProvider.class, remap = false)
public interface DrawerCapacityMixin {
    @Inject(method = "calculateAsFactor(Lnet/neoforged/neoforge/items/IItemHandler;"
            + "Ljava/util/function/Supplier;F[Lnet/minecraft/world/item/ItemStack;)F",
            at = @At("HEAD"), cancellable = true)
    private static void expedition$additive(
            IItemHandler slots, Supplier<DataComponentType<SizeProvider>> component, float base,
            ItemStack[] previews, CallbackInfoReturnable<Float> result) {
        float bonus = 0;
        boolean hasStandardUpgrade = false;
        float otherFactor = 1;
        for (int i = 0; i < slots.getSlots(); i++) {
            ItemStack stack = previews[i] != null ? previews[i] : slots.getStackInSlot(i);
            SizeProvider provider = stack.get(component);
            if (provider instanceof SizeProvider.ModifyFactor standard) {
                bonus += standard.factor();
                hasStandardUpgrade = true;
            } else if (provider != null) {
                otherFactor = provider.applyFactorModifier(otherFactor);
                base = provider.applyBaseModifier(base);
            }
        }
        float factor = (hasStandardUpgrade ? bonus : 1) * otherFactor;
        float value = Math.max(base, 0) * Math.max(factor, 0);
        result.setReturnValue((float) (Math.floor(value * 100) / 100));
    }
}
