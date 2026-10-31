package expedition.performance.client;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
/** Protect the explicitly authorized FHD floor; never respond to FPS or generate frames. */
@Pseudo
@Mixin(targets = "dev.zelo.renderscale.RenderScale", remap = false)
public abstract class RenderResolutionFloor {
    @Inject(method = "getRenderScaleFactor", at = @At("RETURN"), cancellable = true, require = 1)
    private void expedition$minimumDimensions(CallbackInfoReturnable<Double> ci) {
        NativeWindowSize window = (NativeWindowSize) (Object) Minecraft.m_91087_().m_91268_();
        int width = window.expedition$nativeWidth(), height = window.expedition$nativeHeight();
        if (width <= 0 || height <= 0) return;
        double minimum = Math.ceil(Math.max(1920.0/width, 1080.0/height)*1000.0)/1000.0;
        ci.setReturnValue(Math.max(ci.getReturnValue(), Math.min(1.0, minimum)));
    }
}
