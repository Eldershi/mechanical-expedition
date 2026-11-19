package expedition.refinery.mixin;

import blusunrize.immersiveengineering.api.multiblocks.blocks.env.IInitialMultiblockContext;
import blusunrize.immersiveengineering.common.blocks.multiblocks.logic.RefineryLogic;
import expedition.refinery.RefinerySteamPort;
import expedition.refinery.SteamPortAccess;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = RefineryLogic.State.class, remap = false)
public abstract class RefineryStateMixin implements SteamPortAccess {
    @Shadow @Final public RefineryLogic.RefineryTanks tanks;
    @Unique private RefinerySteamPort expedition$steamPort;

    @Inject(method = "<init>", at = @At("RETURN"))
    private void expedition$initSteamPort(IInitialMultiblockContext<RefineryLogic.State> context, CallbackInfo ci) {
        expedition$steamPort = new RefinerySteamPort(tanks.leftInput(), tanks.rightInput(), context.getMarkDirtyRunnable());
    }

    @Override
    public RefinerySteamPort expedition$getSteamPort() {
        return expedition$steamPort;
    }
}
