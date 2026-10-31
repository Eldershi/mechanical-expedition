package expedition.railway.mixin;

import expedition.railway.StructureRailwayAvoidance;
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

@Mixin(value=Structure.class, remap=false)
public abstract class StructureCandidateMixin {
    @Inject(method="m_226596_", at=@At("RETURN"), cancellable=true, remap=false)
    private void expedition$avoidRailway(RegistryAccess registries, ChunkGenerator generator,
        BiomeSource biomes, RandomState noise, StructureTemplateManager templates, long seed,
        ChunkPos pos, int references, LevelHeightAccessor height,
        Predicate<Holder<Biome>> biomePredicate, CallbackInfoReturnable<StructureStart> cir) {
        if (StructureRailwayAvoidance.conflicts(cir.getReturnValue(), generator, seed, height))
            cir.setReturnValue(StructureStart.f_73561_);
    }
}
