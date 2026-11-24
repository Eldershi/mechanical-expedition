package expedition.structurelookup.mixin;

import net.minecraft.world.level.chunk.status.ChunkPyramid;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.chunk.status.ChunkStep;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = ChunkPyramid.class, remap = false)
abstract class FeatureDependenciesMixin {
    @Redirect(method = "lambda$static$7", at = @At(value = "INVOKE", ordinal = 0, target =
        "Lnet/minecraft/world/level/chunk/status/ChunkStep$Builder;addRequirement(Lnet/minecraft/world/level/chunk/status/ChunkStatus;I)Lnet/minecraft/world/level/chunk/status/ChunkStep$Builder;"))
    private static ChunkStep.Builder expedition$includeNeighborStructureStarts(ChunkStep.Builder builder,
            ChunkStatus requirement, int radius) {
        // A feature's search can cross into an adjacent chunk whose references reach this extra ring.
        return builder.addRequirement(requirement, radius + 1);
    }
}
