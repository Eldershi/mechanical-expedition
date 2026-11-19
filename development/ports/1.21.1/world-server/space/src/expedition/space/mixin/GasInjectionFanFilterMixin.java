package expedition.space.mixin;

import com.simibubi.create.content.kinetics.fan.processing.FanProcessingType;
import expedition.space.cooling.CoolingFanProcessing;
import net.ty.createcraftedbeginning.content.airtights.gasinjectionchamber.GasInjectionChamberFilterItem;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Mixin(value = GasInjectionChamberFilterItem.class, remap = false)
abstract class GasInjectionFanFilterMixin {
    @ModifyVariable(method = "create", at = @At("HEAD"), argsOnly = true)
    private static FanProcessingType expedition$useNativeCoolingFilter(FanProcessingType type) {
        return CoolingFanProcessing.nativeType(type);
    }
}
