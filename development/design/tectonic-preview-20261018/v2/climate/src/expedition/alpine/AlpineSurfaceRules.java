package expedition.alpine;
import net.minecraft.util.KeyDispatchDataCodec;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.levelgen.*;

/** Subclass access to Mojang's protected Context/SurfaceRule nested interfaces. */
public final class AlpineSurfaceRules extends SurfaceRules{
    public static RuleSource source(float baseTemperature,boolean steep,ChunkAccess chunk){return new AlpineSource(baseTemperature,steep,chunk);}
    /** Ephemeral buildSurface argument; never stored or serialized in a registry. */
    private record AlpineSource(float baseTemperature,boolean steep,ChunkAccess chunk) implements RuleSource{
        public SurfaceRule apply(Context context){
            return (x,y,z)->{
                if(y!=chunk.m_5885_(Heightmap.Types.WORLD_SURFACE_WG,x&15,z&15))return null;
                double line=ClimateRules.snowline(baseTemperature,x,z);
                if(y<line-ClimateRules.setting("rock_start_below_snowline",32))return null;
                if(steep)return Blocks.f_50069_.m_49966_();
                if(y>=line)return Blocks.f_50127_.m_49966_();
                return Blocks.f_50069_.m_49966_();
            };
        }
        public KeyDispatchDataCodec<? extends RuleSource> m_213795_(){throw new UnsupportedOperationException("Transient alpine surface rule cannot be serialized");}
    }
}
