package expedition.alpine;
import com.mojang.serialization.Codec;
import java.util.stream.Stream;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.levelgen.placement.*;
public final class AlpineTreePlacement extends PlacementModifier{
    public static final AlpineTreePlacement INSTANCE=new AlpineTreePlacement();
    public static final Codec<AlpineTreePlacement> CODEC=Codec.unit(INSTANCE);
    public Stream<BlockPos> m_213676_(PlacementContext context,RandomSource random,BlockPos pos){
        return ClimateRules.allowTree(context.m_191831_(),pos,random)?Stream.of(pos):Stream.empty();
    }
    public PlacementModifierType<?> m_183327_(){return AlpineClimateMod.TREE.get();}
}
