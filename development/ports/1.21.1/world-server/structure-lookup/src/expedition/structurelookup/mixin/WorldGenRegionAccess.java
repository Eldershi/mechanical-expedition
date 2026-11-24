package expedition.structurelookup.mixin;

import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.chunk.status.ChunkStep;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(value = WorldGenRegion.class, remap = false)
public interface WorldGenRegionAccess {
    @Accessor("generatingStep")
    ChunkStep expedition$generatingStep();
}
