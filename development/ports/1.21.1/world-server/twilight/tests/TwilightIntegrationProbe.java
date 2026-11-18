package expedition.twilight.test;

import expedition.twilight.SparseLandmarkPlacement;
import expedition.twilight.TwilightLandmarks;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Optional;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderSet;
import net.minecraft.core.QuartPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import twilightforest.util.landmarks.LegacyLandmarkPlacements;
import twilightforest.world.components.structures.placements.LandmarkGridPlacement;

@Mod("expedition_twilight_integration_probe")
public final class TwilightIntegrationProbe {
    private static final ResourceKey<Level> TWILIGHT = ResourceKey.create(Registries.DIMENSION, id("twilight_forest"));
    private static final ResourceKey<Structure> NAGA = ResourceKey.create(Registries.STRUCTURE, id("naga_courtyard"));
    private static final Path FIXTURE = Path.of("twilight-proof-coordinates.txt");
    private static final List<String> STRUCTURES = List.of("aurora_palace", "hydra_lair", "knight_stronghold",
        "labyrinth", "lich_tower", "naga_courtyard", "troll_cave", "yeti_cave", "dark_tower");

    public TwilightIntegrationProbe() {
        NeoForge.EVENT_BUS.addListener(this::register);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionspecialboss")
            .requires(source -> source.hasPermission(4))
            .then(Commands.literal("generate").executes(context -> verify(context.getSource(), false)))
            .then(Commands.literal("reopen").executes(context -> verify(context.getSource(), true))));
    }

    private int verify(CommandSourceStack source, boolean reopening) {
        try {
            var server = source.getServer();
            var twilight = server.getLevel(TWILIGHT);
            require(twilight != null, "Twilight dimension unavailable");
            verifyPlacements(twilight, server.overworld(), server.getLevel(Level.NETHER), server.getLevel(Level.END));
            if (reopening) reopen(twilight);
            else generate(twilight, server.getLevel(Level.NETHER), server.getLevel(Level.END));
            System.out.println("EXPEDITION_SPECIAL_BOSS_PASS " + (reopening ? "reopen" : "generate"));
            return 1;
        } catch (Exception error) {
            error.printStackTrace();
            System.out.println("EXPEDITION_SPECIAL_BOSS_FAILED " + error);
            return 0;
        }
    }

    private void verifyPlacements(ServerLevel twilight, ServerLevel... otherLevels) {
        var access = twilight.registryAccess();
        var structures = access.registryOrThrow(Registries.STRUCTURE);
        var sets = access.registryOrThrow(Registries.STRUCTURE_SET);
        var state = twilight.getChunkSource().getGeneratorState();
        for (var name : STRUCTURES) {
            var key = ResourceKey.create(Registries.STRUCTURE, id(name));
            var structure = structures.getHolderOrThrow(key);
            var registered = sets.get(id(name));
            require(registered != null && registered.placement() instanceof SparseLandmarkPlacement,
                "unadapted placement " + name);
            var placement = (SparseLandmarkPlacement) registered.placement();
            require(placement.structure().equals(key) && state.getPlacementsForStructure(structure).contains(placement),
                "inactive Twilight placement " + name);
            for (var level : otherLevels) {
                require(level.getChunkSource().getGeneratorState().getPlacementsForStructure(structure).isEmpty(),
                    "Twilight placement present in " + level.dimension().location());
            }
        }
        System.out.println("EXPEDITION_SPECIAL_BOSS_DIMENSIONS twilight=" + STRUCTURES.size() + " others=0");
    }

    private void generate(ServerLevel level, ServerLevel... adjacentLevels) throws Exception {
        var sparse = nagaPlacement(level);
        var state = level.getChunkSource().getGeneratorState();
        var holder = level.registryAccess().registryOrThrow(Registries.STRUCTURE).getHolderOrThrow(NAGA);
        var nativeGrid = new LandmarkGridPlacement(Optional.of(NAGA));
        BlockPos accepted = null;
        BlockPos rejected = null;
        for (var position : LegacyLandmarkPlacements.landmarkCenterScanner(BlockPos.ZERO, 240)) {
            var chunk = new ChunkPos(position);
            if (!nativeGrid.isStructureChunk(state, chunk.x, chunk.z)) continue;
            var biome = level.getUncachedNoiseBiome(QuartPos.fromBlock(position.getX()), 0,
                QuartPos.fromBlock(position.getZ()));
            if (!holder.value().biomes().contains(biome)) continue;
            if (sparse.isStructureChunk(state, chunk.x, chunk.z)) {
                if (accepted == null) accepted = position.immutable();
            } else if (rejected == null) rejected = position.immutable();
            if (accepted != null && rejected != null) break;
        }
        require(accepted != null && rejected != null, "both placement branches need seed-valid candidates");

        var found = locate(level, accepted);
        require(new ChunkPos(accepted).equals(new ChunkPos(found)), "native locate returned " + found);
        var positive = new ChunkPos(found);
        var valid = level.getChunk(positive.x, positive.z, ChunkStatus.FULL, true).getStartForStructure(holder.value());
        require(valid != null && valid.isValid(), "reported Naga courtyard did not generate");
        System.out.println("EXPEDITION_SPECIAL_BOSS_START position=" + found.toShortString()
            + " bounds=" + valid.getBoundingBox() + " pieces=" + valid.getPieces().size());

        var negative = new ChunkPos(rejected);
        var skipped = level.getChunk(negative.x, negative.z, ChunkStatus.STRUCTURE_STARTS, true)
            .getStartForStructure(holder.value());
        require(skipped == null || !skipped.isValid(), "density-filtered Naga courtyard generated anyway");
        for (var adjacent : adjacentLevels) {
            var bioChunk = adjacent.getChunk(128, 128, ChunkStatus.BIOMES, true);
            require(bioChunk != null, "biome generation failed in " + adjacent.dimension().location());
            System.out.println("EXPEDITION_SPECIAL_BOSS_ADJACENT_BIOMES dimension=" + adjacent.dimension().location()
                + " source=" + adjacent.getChunkSource().getGenerator().getBiomeSource().getClass().getSimpleName());
        }
        Files.writeString(FIXTURE, found.getX() + " " + found.getZ() + "\n");
    }

    private void reopen(ServerLevel level) throws Exception {
        var coordinates = Files.readString(FIXTURE).strip().split(" ");
        var position = new BlockPos(Integer.parseInt(coordinates[0]), 0, Integer.parseInt(coordinates[1]));
        var chunk = new ChunkPos(position);
        var sparse = nagaPlacement(level);
        var chunks = level.getChunkSource();
        require(chunks.getChunkNow(chunk.x, chunk.z) == null, "saved test chunk is already loaded");
        require(!sparse.isStructureChunk(chunks.getGeneratorState(), chunk.x, chunk.z),
            "reopen fixture requires a density which now excludes the saved start");
        require(TwilightLandmarks.hasSavedStart(level, sparse, chunk.x, chunk.z), "native storage check lost the start");
        require(chunk.equals(new ChunkPos(locate(level, position))), "native locate missed the saved start");
        require(chunks.getChunkNow(chunk.x, chunk.z) == null, "locate loaded the saved chunk at full status");
        var structure = level.registryAccess().registryOrThrow(Registries.STRUCTURE).getHolderOrThrow(NAGA).value();
        var saved = level.getChunk(chunk.x, chunk.z, ChunkStatus.FULL, true).getStartForStructure(structure);
        require(saved != null && saved.isValid(), "saved Naga courtyard could not be read back");
        System.out.println("EXPEDITION_SPECIAL_BOSS_SAVED position=" + position.toShortString()
            + " pieces=" + saved.getPieces().size());
    }

    private SparseLandmarkPlacement nagaPlacement(ServerLevel level) {
        return (SparseLandmarkPlacement) level.registryAccess().registryOrThrow(Registries.STRUCTURE_SET)
            .get(NAGA.location()).placement();
    }

    private BlockPos locate(ServerLevel level, BlockPos origin) {
        var structure = level.registryAccess().registryOrThrow(Registries.STRUCTURE).getHolderOrThrow(NAGA);
        var found = level.getChunkSource().getGenerator().findNearestMapStructure(level, HolderSet.direct(structure),
            origin, 2, false);
        require(found != null, "native locate could not find " + NAGA.location() + " around " + origin);
        return found.getFirst();
    }

    private static ResourceLocation id(String name) {
        return ResourceLocation.fromNamespaceAndPath("twilightforest", name);
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
