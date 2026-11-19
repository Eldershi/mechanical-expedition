package expedition.refinery.mixin;

import java.util.Set;

import blusunrize.immersiveengineering.api.multiblocks.blocks.component.IMultiblockComponent.CapabilityRegistrar;
import blusunrize.immersiveengineering.api.multiblocks.blocks.util.CapabilityPosition;
import blusunrize.immersiveengineering.common.blocks.multiblocks.logic.RefineryLogic;
import expedition.refinery.SteamPortAccess;
import net.ty.createcraftedbeginning.api.gas.GasCapabilities;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = RefineryLogic.class, remap = false)
public abstract class RefineryLogicMixin {
    @Shadow @Final private static Set<CapabilityPosition> FLUID_INPUT_CAPS;

    @Inject(method = "registerCapabilities", at = @At("TAIL"))
    private void expedition$registerSteamInputs(CapabilityRegistrar<RefineryLogic.State> registrar, CallbackInfo ci) {
        registrar.register(GasCapabilities.BLOCK, (state, position) ->
            FLUID_INPUT_CAPS.contains(position) ? ((SteamPortAccess) state).expedition$getSteamPort() : null);
    }
}
