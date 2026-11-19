package expedition.space.mixin;

import net.minecraft.core.HolderLookup;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.util.Tuple;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "com.bmaster.createrns.content.deposit.mining.behaviour.MiningBehaviour", remap = false)
abstract class PendingMiningProcessMixin {
    @Shadow protected Tuple<CompoundTag, Boolean> pendingProcessTag;

    @Inject(method = "write", at = @At("RETURN"))
    private void expedition$savePendingProcess(
        CompoundTag data, HolderLookup.Provider lookup, boolean clientPacket, CallbackInfo ci
    ) {
        if (!clientPacket && !data.contains("process") && pendingProcessTag != null && !pendingProcessTag.getB()) {
            data.put("process", pendingProcessTag.getA().copy());
        }
    }
}
