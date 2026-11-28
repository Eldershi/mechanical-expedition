package expedition.performance.client;

import com.mojang.blaze3d.platform.GlStateManager;
import com.mojang.blaze3d.systems.RenderSystem;
import expedition.performance.support.BslProfile;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.pipeline.FinalPassRenderer;
import net.irisshaders.iris.targets.RenderTargets;
import net.minecraft.client.Minecraft;
import org.lwjgl.opengl.GL11C;
import org.lwjgl.system.Platform;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = FinalPassRenderer.class, remap = false)
abstract class BslTemporalCopyMixin {
    @Shadow @Final private RenderTargets renderTargets;

    @Unique private static final int expedition$historyWidth = 8;
    @Unique private static final int expedition$historyHeight = 4;

    @Unique private boolean expedition$limitBslTemporalCopy;
    @Unique private boolean expedition$copyingTemporalBuffer;

    @Inject(method = "<init>", at = @At("RETURN"))
    private void expedition$checkTemporalConsumers(CallbackInfo callback) {
        var pack = Iris.getCurrentPack().orElse(null);
        expedition$limitBslTemporalCopy = Platform.get() == Platform.MACOSX && pack != null
            && BslProfile.hasDisabledOptions(pack, "TAA", "DOF")
            && BslProfile.isSupportedArchive()
            && renderTargets.getRenderTargetCount() > 2;
    }

    @Redirect(
        method = "renderFinalPass()V",
        at = @At(value = "INVOKE", target = "Lcom/mojang/blaze3d/systems/RenderSystem;bindTexture(I)V", ordinal = 0)
    )
    private void expedition$bindHistoryTarget(int texture) {
        RenderSystem.bindTexture(texture);
        expedition$copyingTemporalBuffer = expedition$limitBslTemporalCopy && texture > 0
            && texture == renderTargets.get(2).getMainTexture();
    }

    @Redirect(
        method = "renderFinalPass()V",
        at = @At(
            value = "INVOKE",
            target = "Lcom/mojang/blaze3d/platform/GlStateManager;_glCopyTexSubImage2D(IIIIIIII)V"
        )
    )
    private void expedition$copySampledHistory(
        int target, int level, int dstX, int dstY, int srcX, int srcY, int width, int height
    ) {
        if (expedition$copyingTemporalBuffer && target == GL11C.GL_TEXTURE_2D && level == 0
            && dstX == 0 && dstY == 0 && srcX == 0 && srcY == 0
            && width >= expedition$historyWidth && height >= expedition$historyHeight) {
            var main = Minecraft.getInstance().getMainRenderTarget();
            if (width == main.width && height == main.height) {
                // Without TAA or DOF, BSL only samples the corner containing exposure and lens flare history.
                width = expedition$historyWidth;
                height = expedition$historyHeight;
            }
        }
        GlStateManager._glCopyTexSubImage2D(target, level, dstX, dstY, srcX, srcY, width, height);
    }
}
