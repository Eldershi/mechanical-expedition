package expedition.liquefied.mixin;

import expedition.liquefied.PipedLiquids;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.IFluidHandler.FluidAction;
import net.neoforged.neoforge.fluids.capability.wrappers.FluidBucketWrapper;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = FluidBucketWrapper.class, remap = false)
abstract class FluidBucketWrapperMixin {
    @Shadow public abstract FluidStack getFluid();

    @Inject(method = "canFillFluidType", at = @At("HEAD"), cancellable = true)
    private void expeditionRejectLiquefiedGas(FluidStack fluid, CallbackInfoReturnable<Boolean> result) {
        if (PipedLiquids.contains(fluid.getFluid())) result.setReturnValue(false);
    }

    @Inject(
        method = "drain(ILnet/neoforged/neoforge/fluids/capability/IFluidHandler$FluidAction;)Lnet/neoforged/neoforge/fluids/FluidStack;",
        at = @At("HEAD"), cancellable = true
    )
    private void expeditionBlockExistingBucket(int amount, FluidAction action, CallbackInfoReturnable<FluidStack> result) {
        if (PipedLiquids.contains(getFluid().getFluid())) result.setReturnValue(FluidStack.EMPTY);
    }

    @Inject(
        method = "drain(Lnet/neoforged/neoforge/fluids/FluidStack;Lnet/neoforged/neoforge/fluids/capability/IFluidHandler$FluidAction;)Lnet/neoforged/neoforge/fluids/FluidStack;",
        at = @At("HEAD"), cancellable = true
    )
    private void expeditionBlockRequestedDrain(
        FluidStack requested, FluidAction action, CallbackInfoReturnable<FluidStack> result
    ) {
        if (PipedLiquids.contains(getFluid().getFluid())) result.setReturnValue(FluidStack.EMPTY);
    }
}
