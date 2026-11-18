package expedition.railway.mixin;

import expedition.railway.RailwayAvoidance;
import net.minecraft.core.RegistryAccess;
import net.minecraft.server.level.GenerationChunkHolder;
import net.minecraft.util.StaticCache2D;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.chunk.status.ChunkStatusTasks;
import net.minecraft.world.level.chunk.status.ChunkStep;
import net.minecraft.world.level.chunk.status.WorldGenContext;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = ChunkStatusTasks.class, remap = false)
public abstract class StructureStageMixin {
    @Redirect(method = "generateStructureStarts", at = @At(value = "INVOKE", target =
        "Lnet/minecraft/world/level/chunk/ChunkGenerator;createStructures(Lnet/minecraft/core/RegistryAccess;Lnet/minecraft/world/level/chunk/ChunkGeneratorStructureState;Lnet/minecraft/world/level/StructureManager;Lnet/minecraft/world/level/chunk/ChunkAccess;Lnet/minecraft/world/level/levelgen/structure/templatesystem/StructureTemplateManager;)V"))
    private static void expedition$generation(ChunkGenerator generator, RegistryAccess registries,
            ChunkGeneratorStructureState state, StructureManager manager, ChunkAccess chunk,
            StructureTemplateManager templates, WorldGenContext context, ChunkStep step,
            StaticCache2D<GenerationChunkHolder> cache, ChunkAccess mainChunk) {
        RailwayAvoidance.duringStructureStarts(context, step, cache, mainChunk,
            () -> generator.createStructures(registries, state, manager, chunk, templates));
    }
}
