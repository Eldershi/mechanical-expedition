package expedition.compat;

import org.popcraft.chunky.ChunkyProvider;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Defer DH's optional Chunky subscription until Chunky has a server instance. */
@Mixin(targets = "com.seibel.distanthorizons.core.wrapperInterfaces.modAccessor.AbstractChunkyAccessor", remap = false)
public abstract class ChunkyStartupGuard {
    @Unique private static boolean expedition$reportedDelay;
    @Inject(method = "tryRunFirstTimeSetup", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$waitForChunky(CallbackInfo callback) {
        try {
            ChunkyProvider.get();
        } catch (IllegalStateException exception) {
            if (!"Chunky is not loaded.".equals(exception.getMessage())) throw exception;
            if (!expedition$reportedDelay) {
                System.out.println("[Expedition compatibility] Deferred DH / Chunky subscription until Chunky server initialization.");
                expedition$reportedDelay = true;
            }
            // Do not set DH's listenerBound flag. The next chunk update retries.
            callback.cancel();
        }
    }
}
