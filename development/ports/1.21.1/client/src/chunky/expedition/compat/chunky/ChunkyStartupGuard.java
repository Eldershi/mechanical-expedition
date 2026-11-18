package expedition.compat.chunky;

import org.popcraft.chunky.ChunkyProvider;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Leave the listener unbound until Chunky has set up the integrated server. */
@Mixin(targets = "com.seibel.distanthorizons.core.wrapperInterfaces.modAccessor.AbstractChunkyAccessor",
    remap = false)
abstract class ChunkyStartupGuard {
    @Shadow private boolean listenerBound;

    @Inject(method = "tryRunFirstTimeSetup()V", at = @At("HEAD"), cancellable = true, require = 1)
    private void expedition$waitForChunky(CallbackInfo callback) {
        if (listenerBound) return;
        try {
            ChunkyProvider.get();
        } catch (IllegalStateException exception) {
            if (!"Chunky is not loaded.".equals(exception.getMessage())) throw exception;
            callback.cancel();
        }
    }
}
