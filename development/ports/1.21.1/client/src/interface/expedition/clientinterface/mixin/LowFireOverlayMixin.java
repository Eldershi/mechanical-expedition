package expedition.clientinterface.mixin;

import net.minecraft.client.renderer.ScreenEffectRenderer;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.Constant;
import org.spongepowered.asm.mixin.injection.ModifyConstant;

@Mixin(ScreenEffectRenderer.class)
abstract class LowFireOverlayMixin {
    @ModifyConstant(method = "renderFire", constant = @Constant(floatValue = -0.3F), require = 1, allow = 1)
    private static float expedition$lowerFireOverlay(float original) {
        return -0.55F;
    }

    @ModifyConstant(method = "renderFire", constant = @Constant(floatValue = 0.9F), require = 4, allow = 4)
    private static float expedition$softenFireOverlay(float original) {
        return 0.64F;
    }
}
