package expedition.twilight;

import com.mojang.serialization.Codec;
import com.mojang.serialization.MapCodec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.Optional;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.StructurePlacementType;
import twilightforest.world.components.structures.placements.LandmarkGridPlacement;

public final class SparseLandmarkPlacement extends LandmarkGridPlacement {
    private static final Codec<ResourceKey<Structure>> STRUCTURE = ResourceKey.codec(Registries.STRUCTURE);
    public static final MapCodec<SparseLandmarkPlacement> CODEC = RecordCodecBuilder.mapCodec(builder -> builder.group(
        STRUCTURE.optionalFieldOf("structure_grid_lock").forGetter(placement -> placement.gridLock),
        STRUCTURE.fieldOf("structure").forGetter(SparseLandmarkPlacement::structure)
    ).apply(builder, SparseLandmarkPlacement::new));

    private final Optional<ResourceKey<Structure>> gridLock;
    private final ResourceKey<Structure> structure;

    public SparseLandmarkPlacement(Optional<ResourceKey<Structure>> gridLock, ResourceKey<Structure> structure) {
        super(gridLock);
        this.gridLock = gridLock;
        this.structure = structure;
    }

    public ResourceKey<Structure> structure() {
        return structure;
    }

    @Override
    protected boolean isPlacementChunk(ChunkGeneratorStructureState state, int x, int z) {
        return super.isPlacementChunk(state, x, z) && TwilightLandmarks.allows(structure, state.getLevelSeed(), x, z);
    }

    @Override
    public StructurePlacementType<?> type() {
        return TwilightLandmarks.SPARSE.get();
    }
}
