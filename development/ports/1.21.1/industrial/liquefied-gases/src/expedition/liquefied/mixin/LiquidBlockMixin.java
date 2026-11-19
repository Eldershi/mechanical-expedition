package expedition.liquefied.mixin;

import expedition.liquefied.PipedLiquids;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.block.LiquidBlock;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(LiquidBlock.class)
abstract class LiquidBlockMixin {
    @Inject(method = "pickupBlock", at = @At("HEAD"), cancellable = true, remap = false)
    private void expeditionPreventScooping(
        Player player, LevelAccessor level, BlockPos pos, BlockState state, CallbackInfoReturnable<ItemStack> result
    ) {
        if (PipedLiquids.contains(state.getFluidState().getType())) result.setReturnValue(ItemStack.EMPTY);
    }
}
