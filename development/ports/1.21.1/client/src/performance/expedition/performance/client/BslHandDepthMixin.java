package expedition.performance.client;

import expedition.performance.support.BslProfile;
import net.irisshaders.iris.pipeline.IrisRenderingPipeline;
import net.irisshaders.iris.shaderpack.programs.ProgramSet;
import net.irisshaders.iris.targets.RenderTargets;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = IrisRenderingPipeline.class, remap = false)
abstract class BslHandDepthMixin {
    @Unique
    private boolean expedition$skipUnusedHandDepth;

    @Inject(method = "<init>(Lnet/irisshaders/iris/shaderpack/programs/ProgramSet;)V", at = @At("RETURN"))
    private void expedition$checkHandDepthConsumers(ProgramSet programs, CallbackInfo callback) {
        // BSL's only consumers of depthtex2 are the motion blur and depth of field passes.
        expedition$skipUnusedHandDepth = BslProfile.hasDisabledOptions(programs.getPack(), "MOTION_BLUR", "DOF")
            && BslProfile.isSupportedArchive();
    }

    @Redirect(
        method = "beginHand()V",
        at = @At(value = "INVOKE", target = "Lnet/irisshaders/iris/targets/RenderTargets;copyPreHandDepth()V")
    )
    private void expedition$copyHandDepthWhenUsed(RenderTargets targets) {
        if (!expedition$skipUnusedHandDepth) {
            targets.copyPreHandDepth();
        }
    }
}
