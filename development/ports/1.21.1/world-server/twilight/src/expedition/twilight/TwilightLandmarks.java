package expedition.twilight;

import expedition.worldgen.BossDensityPolicy;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.StructurePlacementType;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.registries.DeferredHolder;
import net.neoforged.neoforge.registries.DeferredRegister;

@Mod("expedition_worldgen_compat")
public final class TwilightLandmarks {
    private static final DeferredRegister<StructurePlacementType<?>> TYPES =
        DeferredRegister.create(BuiltInRegistries.STRUCTURE_PLACEMENT, "expedition_worldgen_compat");
    static final DeferredHolder<StructurePlacementType<?>, StructurePlacementType<SparseLandmarkPlacement>> SPARSE =
        TYPES.register("sparse_landmark", () -> () -> SparseLandmarkPlacement.CODEC);

    public TwilightLandmarks(IEventBus bus) {
        TYPES.register(bus);
    }

    public static boolean allows(ResourceKey<Structure> structure, long seed, int chunkX, int chunkZ) {
        return BossDensityPolicy.allowsId(structure.location().toString(), seed, chunkX, chunkZ);
    }

    public static boolean hasExistingStart(ServerLevel level, ResourceKey<Structure> id, int chunkX, int chunkZ) {
        var chunk = level.getChunkSource().getChunkNow(chunkX, chunkZ);
        if (chunk == null) {
            return false;
        }
        return level.registryAccess().registryOrThrow(Registries.STRUCTURE).getHolder(id).map(holder -> {
            var start = chunk.getStartForStructure(holder.value());
            return start != null && start.isValid();
        }).orElse(false);
    }
}
