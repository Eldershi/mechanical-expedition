package expedition.alpine.mixin;
import expedition.alpine.ClimateRules;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.biome.Biome;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
@Mixin(value=Biome.class,remap=false)
public abstract class BiomeTemperatureMixin{
    @Inject(method="m_47505_",at=@At("RETURN"),cancellable=true,remap=false)
    private void alpine$temperature(BlockPos actualPosition,CallbackInfoReturnable<Float> callback){
        callback.setReturnValue(ClimateRules.temperature((Biome)(Object)this,actualPosition,callback.getReturnValue()));
    }
}
