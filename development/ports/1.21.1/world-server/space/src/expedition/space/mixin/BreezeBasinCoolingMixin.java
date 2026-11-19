package expedition.space.mixin;

import com.simibubi.create.content.processing.basin.BasinBlockEntity;
import expedition.space.cooling.CoolingSources;
import net.ty.createcraftedbeginning.content.breezes.breezecooler.BreezeCoolerBasinCooling;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = BreezeCoolerBasinCooling.class, remap = false)
abstract class BreezeBasinCoolingMixin {
    @Inject(method = "hasChilledSource", at = @At("RETURN"), cancellable = true)
    private static void expedition$allowSnowGolem(BasinBlockEntity basin, CallbackInfoReturnable<Boolean> result) {
        if (!result.getReturnValueZ() && CoolingSources.hasSnowGolemBelow(basin)) result.setReturnValue(true);
    }
}
