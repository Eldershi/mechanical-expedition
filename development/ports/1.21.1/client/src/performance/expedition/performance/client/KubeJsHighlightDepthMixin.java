package expedition.performance.client;

import dev.latvian.mods.kubejs.client.highlight.HighlightRenderer;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = HighlightRenderer.class, remap = false)
abstract class KubeJsHighlightDepthMixin {
    @Redirect(
        method = "updateDepth(Lnet/minecraft/client/Minecraft;)V",
        at = @At(
            value = "INVOKE",
            target = "Ldev/latvian/mods/kubejs/client/highlight/HighlightRenderer$ShaderChain;"
                + "clearDepth(Lnet/minecraft/client/Minecraft;Z)V",
            ordinal = 0
        )
    )
    private void expedition$copyWorldDepthForHighlights(
        HighlightRenderer.ShaderChain chain, Minecraft client, boolean copyWorldDepth
    ) {
        chain.clearDepth(client, copyWorldDepth && chain.renderAnything().booleanValue());
    }
}
