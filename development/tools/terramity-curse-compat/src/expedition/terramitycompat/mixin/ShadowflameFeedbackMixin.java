package expedition.terramitycompat.mixin;
import expedition.terramitycompat.TerramityCurseCompat;
import net.minecraftforge.event.entity.living.LivingAttackEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** The same burning tick must not renew Eternal Shadowflame indefinitely. */
@Mixin(targets="net.mcreator.terramity.procedures.EternalShadowflameProcProcedure",remap=false)
public abstract class ShadowflameFeedbackMixin {
    @Inject(method="onEntityAttacked",at=@At("HEAD"),cancellable=true,remap=false,require=1,allow=1)
    private static void expedition$preventFeedback(LivingAttackEvent event,CallbackInfo ci) {
        if(TerramityCurseCompat.applyingDamage()) ci.cancel();
    }
}
