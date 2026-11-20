package expedition.curserules.mixin;

import com.ninni.spawn.server.gui.fly.FlyCapabilityProvider;
import com.ninni.spawn.server.gui.fly.FlyData;
import java.util.ArrayList;
import java.util.List;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = FlyCapabilityProvider.class, remap = false)
abstract class FlyAttachmentsMixin {
    @Inject(method = "getFlies", at = @At("HEAD"), cancellable = true)
    private void expeditionDisableFlyEffects(CallbackInfoReturnable<List<FlyData>> callback) {
        // Callers may mutate the returned list. Keep their changes out of the saved attachment.
        callback.setReturnValue(new ArrayList<>());
    }
}
