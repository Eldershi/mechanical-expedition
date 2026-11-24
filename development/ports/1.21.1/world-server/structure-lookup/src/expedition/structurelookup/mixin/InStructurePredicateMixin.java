package expedition.structurelookup.mixin;

import dev.worldgen.lithostitched.worldgen.blockpredicate.InStructurePredicate;
import it.unimi.dsi.fastutil.longs.LongSet;
import java.util.HashMap;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.WorldGenLevel;
import net.minecraft.world.level.chunk.status.ChunkDependencies;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = InStructurePredicate.class, remap = false)
abstract class InStructurePredicateMixin {
    @Shadow public abstract Optional<Holder<Structure>> structure();
    @Shadow public abstract InStructurePredicate.SearchRange searchRange();

    @Inject(method = "test(Lnet/minecraft/world/level/WorldGenLevel;Lnet/minecraft/core/BlockPos;)Z",
            at = @At("HEAD"), cancellable = true)
    private void expedition$useGenerationDependencies(WorldGenLevel level, BlockPos pos,
            CallbackInfoReturnable<Boolean> callback) {
        if (!(level instanceof WorldGenRegion region)) {
            return;
        }
        var step = ((WorldGenRegionAccess) region).expedition$generatingStep();
        if (step.targetStatus() != ChunkStatus.FEATURES) {
            return;
        }
        var dependencies = step.directDependencies();
        var center = region.getCenter();
        var bounds = searchRange().box().moved(pos.getX(), pos.getY(), pos.getZ());
        var references = new HashMap<Structure, LongSet>();
        for (var chunks = bounds.intersectingChunks().iterator(); chunks.hasNext();) {
            var chunk = chunks.next();
            if (!expedition$covers(dependencies, center, chunk.x, chunk.z, ChunkStatus.STRUCTURE_REFERENCES)) {
                return;
            }
            references.putAll(region.getChunk(chunk.x, chunk.z, ChunkStatus.STRUCTURE_REFERENCES, false)
                .getAllReferences());
        }

        var selected = structure().map(Holder::value).orElse(null);
        for (var entry : references.entrySet()) {
            if (selected != null && !selected.equals(entry.getKey())) {
                continue;
            }
            for (var starts = entry.getValue().iterator(); starts.hasNext();) {
                long packed = starts.nextLong();
                int x = ChunkPos.getX(packed);
                int z = ChunkPos.getZ(packed);
                if (!expedition$covers(dependencies, center, x, z, ChunkStatus.STRUCTURE_STARTS)) {
                    return;
                }
                var start = region.getChunk(x, z, ChunkStatus.STRUCTURE_STARTS, false)
                    .getStartForStructure(entry.getKey());
                if (start != null && start.isValid()) {
                    for (var piece : start.getPieces()) {
                        if (piece.getBoundingBox().intersects(bounds)) {
                            callback.setReturnValue(true);
                            return;
                        }
                    }
                }
            }
        }
        callback.setReturnValue(false);
    }

    @Unique
    private static boolean expedition$covers(ChunkDependencies dependencies, ChunkPos center,
            int x, int z, ChunkStatus status) {
        int distance = center.getChessboardDistance(x, z);
        return distance < dependencies.size() && status.isOrBefore(dependencies.get(distance));
    }
}
