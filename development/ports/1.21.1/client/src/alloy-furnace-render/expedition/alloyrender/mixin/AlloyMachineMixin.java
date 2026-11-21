package expedition.alloyrender.mixin;

import com.lowdragmc.mbd2.common.machine.MBDMachine;
import expedition.alloyrender.AlloyFurnaceRender;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = MBDMachine.class, remap = false)
abstract class AlloyMachineMixin {
    @Inject(method = "clientTick", at = @At("TAIL"))
    private void expedition$updateAlloyRender(CallbackInfo callback) {
        AlloyFurnaceRender.tick((MBDMachine) (Object) this);
    }

    @Inject(method = "onUnload", at = @At("HEAD"))
    private void expedition$removeAlloyRender(CallbackInfo callback) {
        MBDMachine machine = (MBDMachine) (Object) this;
        if (machine.getLevel() != null && machine.getLevel().isClientSide()) AlloyFurnaceRender.remove(machine);
    }
}
