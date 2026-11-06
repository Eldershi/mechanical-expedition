package expedition.terramitycompat.mixin;
import expedition.terramitycompat.TerramityCurseCompat;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.damagesource.DamageSource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets="net.mcreator.terramity.procedures.NyxiumFireOnEffectActiveTickProcedure",remap=false)
public abstract class ShadowflameDamageMixin {
    @Redirect(method="execute",at=@At(value="INVOKE",target="Lnet/minecraft/world/entity/Entity;m_6469_(Lnet/minecraft/world/damagesource/DamageSource;F)Z"),remap=false,require=1,allow=1)
    private static boolean expedition$attributeShadowflame(Entity target,DamageSource source,float amount) {
        return TerramityCurseCompat.hurt(target,source,amount);
    }
}
