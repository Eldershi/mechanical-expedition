package expedition.worldgen.mixin;

import expedition.worldgen.BossDensityPolicy;

import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Both native eligibility paths are thinned identically; native /locate uses the first. */
@Mixin(targets="twilightforest.world.components.structures.placements.BiomeForcedLandmarkPlacement",remap=false)
public abstract class TwilightBossDensity {
    @Inject(method="isTFPlacementChunk",at=@At("HEAD"),cancellable=true,remap=false)
    private void expedition$forced(ChunkGenerator generator,ChunkGeneratorStructureState state,int x,int z,CallbackInfoReturnable<Boolean> cir) {
        if(!BossDensityPolicy.allows(this,state.m_254887_(),x,z))cir.setReturnValue(false);
    }
    @Inject(method="m_214090_",at=@At("HEAD"),cancellable=true,remap=false)
    private void expedition$legacy(ChunkGeneratorStructureState state,int x,int z,CallbackInfoReturnable<Boolean> cir) {
        if(!BossDensityPolicy.allows(this,state.m_254887_(),x,z))cir.setReturnValue(false);
    }
}
