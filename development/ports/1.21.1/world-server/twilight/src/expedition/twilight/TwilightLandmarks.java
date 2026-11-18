package expedition.twilight;

import expedition.worldgen.BossDensityPolicy;
import java.nio.file.Files;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.dimension.DimensionType;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureCheckResult;
import net.minecraft.world.level.levelgen.structure.placement.StructurePlacementType;
import net.minecraft.world.level.storage.LevelResource;
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

    public static boolean hasSavedStart(ServerLevel level, SparseLandmarkPlacement placement, int x, int z) {
        var chunkSource = level.getChunkSource();
        if (chunkSource.getChunkNow(x, z) != null) {
            return hasExistingStart(level, placement.structure(), x, z);
        }
        var position = new ChunkPos(x, z);
        var region = DimensionType.getStorageFolder(level.dimension(), level.getServer().getWorldPath(LevelResource.ROOT))
            .resolve("region").resolve("r." + position.getRegionX() + "." + position.getRegionZ() + ".mca");
        if (!Files.isRegularFile(region)) {
            return false;
        }
        return level.registryAccess().registryOrThrow(Registries.STRUCTURE).getHolder(placement.structure())
            .map(holder -> level.structureManager().checkStructurePresence(position, holder.value(), placement, false)
                == StructureCheckResult.START_PRESENT)
            .orElse(false);
    }
}
