package expedition.worldgen.mixin;

import expedition.worldgen.BossDensityPolicy;

import java.util.Optional;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Reject only columns that cannot pass the original center-biome check at any Y. */
@Pseudo
@Mixin(targets="com.mega.revelationfix.common.structures.FrostyardStructure",remap=false)
public abstract class FrostyardEarlyBiomeCheck {
    @Inject(method="m_214086_",at=@At("HEAD"),cancellable=true,remap=false)
    private void expedition$earlyBiome(Structure.GenerationContext context,
            CallbackInfoReturnable<Optional<Structure.GenerationStub>> cir) {
        int qx=context.f_226628_().m_151390_()>>2;
        int qz=context.f_226628_().m_151393_()>>2;
        int low=context.f_226629_().m_141937_()>>2;
        int high=(context.f_226629_().m_151558_()+3)>>2;
        for(int qy=low;qy<=high;qy++) {
            if(context.f_226630_().test(context.f_226623_().m_203407_(qx,qy,qz,context.f_226624_().m_224579_())))return;
        }
        cir.setReturnValue(Optional.empty());
    }
}
