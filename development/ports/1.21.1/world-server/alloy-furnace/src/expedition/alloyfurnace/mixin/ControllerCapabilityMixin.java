package expedition.alloyfurnace.mixin;

import com.lowdragmc.mbd2.common.machine.MBDMachine;
import com.lowdragmc.mbd2.common.trait.SimpleCapabilityTraitDefinition;
import expedition.alloyfurnace.AlloyFurnace;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(SimpleCapabilityTraitDefinition.Type.class)
abstract class ControllerCapabilityMixin {
    // An empty handler still looks like an attachment to Create pipes.
    @Inject(method = "getCapContent", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$usePhysicalPorts(MBDMachine machine, Object side, CallbackInfoReturnable<Object> callback) {
        if (AlloyFurnace.isController(machine)) callback.setReturnValue(null);
    }
}
