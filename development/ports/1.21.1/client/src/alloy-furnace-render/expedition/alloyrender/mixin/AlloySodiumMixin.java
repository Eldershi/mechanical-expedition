package expedition.alloyrender.mixin;

import expedition.alloyrender.AlloyFurnaceRender;
import net.minecraft.client.resources.model.BakedModel;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.state.BlockState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.caffeinemc.mods.sodium.client.render.chunk.compile.pipeline.BlockRenderer", remap = false)
abstract class AlloySodiumMixin {
    @Inject(method = "renderModel", at = @At("HEAD"), cancellable = true)
    private void expedition$hideFormedSkin(BakedModel model, BlockState state, BlockPos pos,
                                           BlockPos origin, CallbackInfo callback) {
        if (AlloyFurnaceRender.hides(pos, state)) callback.cancel();
    }
}
