package expedition.liquefied.mixin;

import expedition.liquefied.PipedLiquids;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.BlockAndTintGetter;
import net.minecraft.world.level.material.FluidState;
import net.neoforged.neoforge.fluids.FluidType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = FluidType.class, remap = false)
abstract class FluidTypeMixin {
    @Inject(
        method = "canBePlacedInLevel(Lnet/minecraft/world/level/BlockAndTintGetter;Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/material/FluidState;)Z",
        at = @At("HEAD"), cancellable = true
    )
    private void expeditionKeepInPipes(
        BlockAndTintGetter level, BlockPos pos, FluidState state, CallbackInfoReturnable<Boolean> result
    ) {
        if (PipedLiquids.contains(state.getType())) result.setReturnValue(false);
    }
}
