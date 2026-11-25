package expedition.villagetreelookup.mixin;

import com.llamalad7.mixinextras.injector.wrapmethod.WrapMethod;
import com.llamalad7.mixinextras.injector.wrapoperation.Operation;
import expedition.structurelookup.mixin.WorldGenRegionAccess;
import expedition.villagetreelookup.TreeGenerationContext;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.feature.FeaturePlaceContext;
import net.minecraft.world.level.levelgen.feature.TreeFeature;
import net.minecraft.world.level.levelgen.feature.configurations.TreeConfiguration;
import org.spongepowered.asm.mixin.Mixin;

@Mixin(value = TreeFeature.class, remap = false)
abstract class TreeFeatureMixin {
    @WrapMethod(method = "place(Lnet/minecraft/world/level/levelgen/feature/FeaturePlaceContext;)Z")
    private boolean expedition$withTreeGenerationRegion(FeaturePlaceContext<TreeConfiguration> context,
            Operation<Boolean> original) {
        if (!(context.level() instanceof WorldGenRegion region)
                || ((WorldGenRegionAccess) region).expedition$generatingStep().targetStatus() != ChunkStatus.FEATURES
                || region.getCenter().getChessboardDistance(new ChunkPos(context.origin())) > 1) {
            return original.call(context);
        }
        var previous = TreeGenerationContext.current();
        TreeGenerationContext.set(region);
        try {
            return original.call(context);
        } finally {
            TreeGenerationContext.set(previous);
        }
    }
}
