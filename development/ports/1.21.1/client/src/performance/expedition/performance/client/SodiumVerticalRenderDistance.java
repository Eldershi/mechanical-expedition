package expedition.performance.client;

import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "net.caffeinemc.mods.sodium.client.render.chunk.occlusion.OcclusionCuller", remap = false)
abstract class SodiumVerticalRenderDistance {
    // Sodium's horizontal distance test still determines the terrain radius.
    @Redirect(
        method = "isWithinRenderDistance",
        at = @At(value = "INVOKE", target = "Ljava/lang/Math;abs(F)F", remap = false),
        remap = false
    )
    private static float expedition$ignoreVerticalDistance(float distance) {
        return 0.0f;
    }
}
