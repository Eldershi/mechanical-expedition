package expedition.space.mixin;

import com.simibubi.create.content.processing.basin.BasinRecipe;
import org.spongepowered.asm.mixin.Mixin;

// Apply the Fluid Logistics callback adapter after its native mixin.
@Mixin(value = BasinRecipe.class, priority = 900, remap = false)
abstract class FluidLogisticsBasinMixin {}
