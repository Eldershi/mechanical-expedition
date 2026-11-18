package expedition.iemachines.mixin;

import blusunrize.immersiveengineering.common.blocks.metal.FluidPipeBlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = FluidPipeBlockEntity.class, remap = false)
abstract class FluidPipeConnectionMixin {
    @Shadow
    private byte connections;

    @Inject(method = "getAvailableConnectionByte()B", at = @At("HEAD"), cancellable = true)
    private void expedition$useStoredConnectionsUntilPlaced(CallbackInfoReturnable<Byte> result) {
        var pipe = (FluidPipeBlockEntity) (Object) this;
        if (pipe.getLevel() == null) {
            result.setReturnValue(connections);
        }
    }
}
