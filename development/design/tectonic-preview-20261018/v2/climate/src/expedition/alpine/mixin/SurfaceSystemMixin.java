package expedition.alpine.mixin;
import expedition.alpine.ClimateRules;
import net.minecraft.core.Registry;
import net.minecraft.world.level.biome.*;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.*;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
@Mixin(value=SurfaceSystem.class,remap=false)
public abstract class SurfaceSystemMixin{
    @ModifyVariable(method="m_224648_",at=@At("HEAD"),argsOnly=true,ordinal=0,remap=false)
    private SurfaceRules.RuleSource alpine$surface(SurfaceRules.RuleSource original,RandomState random,BiomeManager manager,
            Registry<Biome> biomes,boolean legacy,WorldGenerationContext context,ChunkAccess chunk,NoiseChunk noise,SurfaceRules.RuleSource ignored){
        return ClimateRules.wrap((SurfaceSystem)(Object)this,original,biomes,chunk);
    }
}
