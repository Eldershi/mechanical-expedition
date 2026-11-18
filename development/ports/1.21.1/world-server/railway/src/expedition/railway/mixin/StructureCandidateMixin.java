package expedition.railway.mixin;

import expedition.railway.RailwayAvoidance;
import java.util.function.Predicate;
import net.minecraft.core.Holder;
import net.minecraft.core.RegistryAccess;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.BiomeSource;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplateManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = Structure.class, remap = false)
public abstract class StructureCandidateMixin {
    @Inject(method = "generate", at = @At("RETURN"), cancellable = true)
    private void expedition$avoidRailways(RegistryAccess registries, ChunkGenerator generator, BiomeSource source,
            RandomState random, StructureTemplateManager templates, long seed, ChunkPos pos, int references,
            LevelHeightAccessor height, Predicate<Holder<Biome>> biomes, CallbackInfoReturnable<StructureStart> cir) {
        if (RailwayAvoidance.conflicts(cir.getReturnValue(), seed)) {
            cir.setReturnValue(StructureStart.INVALID_START);
        }
    }
}
