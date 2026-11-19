package expedition.liquefied.mixin;

import expedition.liquefied.PipedLiquids;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.material.Fluid;
import net.neoforged.neoforge.fluids.BaseFlowingFluid;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = BaseFlowingFluid.class, remap = false)
abstract class BaseFlowingFluidMixin {
    @Inject(method = "getBucket", at = @At("HEAD"), cancellable = true)
    private void expeditionHideBucketFromFilling(CallbackInfoReturnable<Item> result) {
        if (PipedLiquids.contains((Fluid) (Object) this)) result.setReturnValue(Items.AIR);
    }
}
