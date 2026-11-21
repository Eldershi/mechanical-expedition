package expedition.alloyrender.mixin;

import expedition.alloyrender.AlloyFurnaceRender;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "com.railwayteam.railways.content.smokestack.block.SmokeStackBlock", remap = false)
abstract class AlloySmokeMixin {
    @Inject(method = "blockEntityAnimateTick", at = @At("HEAD"), cancellable = true)
    private void expedition$useFurnaceExhaust(BlockState state, Level level, BlockPos pos,
                                             RandomSource random, CallbackInfo callback) {
        if (level.isClientSide() && AlloyFurnaceRender.hides(pos, state)) callback.cancel();
    }
}
