package expedition.clientinterface.mixin;

import com.sighs.sophisticatedsorter.common.ContainerScreenController;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = ContainerScreenController.class, remap = false)
abstract class SorterControlsMixin {
    @Inject(method = "initialize", at = @At("RETURN"), cancellable = true)
    private void expedition$useQuarkControls(boolean creative, boolean valid, boolean inventory,
            boolean sophisticated, CallbackInfoReturnable<Boolean> callback) {
        callback.setReturnValue(false);
    }
}
