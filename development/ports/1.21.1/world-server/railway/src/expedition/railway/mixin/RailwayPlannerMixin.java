package expedition.railway.mixin;

import com.hxzhitang.tongdarailway.railway.RailwayBuilder;
import expedition.railway.RailwayAvoidance;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = RailwayBuilder.class, remap = false)
public abstract class RailwayPlannerMixin {
    @Inject(method = "getInstance(J)Lcom/hxzhitang/tongdarailway/railway/RailwayBuilder;",
            at = @At("HEAD"), cancellable = true)
    private static void expedition$useFullFootprint(long seed, CallbackInfoReturnable<RailwayBuilder> cir) {
        // TongDa's structure check uses this overload. The full-piece check uses the world-generation context.
        if (RailwayAvoidance.testsFullStructure()) {
            cir.setReturnValue(null);
        }
    }
}
