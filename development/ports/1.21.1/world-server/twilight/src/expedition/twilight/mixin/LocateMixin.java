package expedition.twilight.mixin;

import expedition.twilight.SparseLandmarkPlacement;
import expedition.twilight.TwilightLandmarks;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderSet;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import twilightforest.util.WorldUtil;
import twilightforest.world.components.structures.placements.LandmarkGridPlacement;

@Mixin(value = WorldUtil.class, remap = false)
public abstract class LocateMixin {
    @Redirect(method = "findNearestMapLandmark", at = @At(value = "INVOKE", target =
        "Ltwilightforest/world/components/structures/placements/LandmarkGridPlacement;isStructureChunk(Lnet/minecraft/world/level/chunk/ChunkGeneratorStructureState;II)Z"))
    private static boolean expedition$includeExistingLandmarks(LandmarkGridPlacement placement,
            ChunkGeneratorStructureState state, int x, int z, ServerLevel level, HolderSet<Structure> structures,
            BlockPos origin, int radius, boolean skipExisting) {
        return placement.isStructureChunk(state, x, z)
            || (!skipExisting && placement instanceof SparseLandmarkPlacement sparse
                && TwilightLandmarks.hasExistingStart(level, sparse.structure(), x, z));
    }
}
