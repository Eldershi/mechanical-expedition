package expedition.alpine;
import com.mojang.serialization.MapCodec;
import java.util.stream.Stream;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.level.levelgen.placement.*;
public final class AlpineTreePlacement extends PlacementModifier{
    public static final AlpineTreePlacement INSTANCE=new AlpineTreePlacement();
    public static final MapCodec<AlpineTreePlacement> CODEC=MapCodec.unit(INSTANCE);
    public Stream<BlockPos> getPositions(PlacementContext context,RandomSource random,BlockPos pos){
        return ClimateRules.allowTree(context.getLevel(),pos,random)?Stream.of(pos):Stream.empty();
    }
    public PlacementModifierType<?> type(){return AlpineClimateMod.TREE.get();}
}
