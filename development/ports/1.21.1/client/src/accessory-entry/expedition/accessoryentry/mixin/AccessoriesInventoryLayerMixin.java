package expedition.accessoryentry.mixin;

import io.wispforest.accessories.client.AccessoriesClient;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = AccessoriesClient.class, remap = false)
abstract class AccessoriesInventoryLayerMixin {
    @Inject(method = "initLayer", at = @At("HEAD"), cancellable = true)
    private static void expedition$replaceInventoryButton(CallbackInfo callback) {
        callback.cancel();
    }
}
