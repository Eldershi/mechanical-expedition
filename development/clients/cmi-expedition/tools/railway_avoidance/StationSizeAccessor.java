package expedition.railway.mixin;

import com.xkmxz.tongdarailway_for_forge.structure.StationStructure;
import net.minecraft.core.BlockPos;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(value=StationStructure.class, remap=false)
public interface StationSizeAccessor {
    @Accessor("size") BlockPos expedition$size();
}
