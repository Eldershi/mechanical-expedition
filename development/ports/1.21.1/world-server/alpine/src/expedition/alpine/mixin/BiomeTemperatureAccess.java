package expedition.alpine.mixin;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.biome.Biome;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Invoker;
@Mixin(value=Biome.class,remap=false)
public interface BiomeTemperatureAccess{
    @Invoker(value="getTemperature",remap=false)
    float alpine$readTemperature(BlockPos pos);
}
