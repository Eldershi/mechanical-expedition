package expedition.worldgen.mixin;

import net.minecraft.core.Holder;
import net.minecraft.world.level.biome.Biome;
import net.minecraft.world.level.biome.Climate;
import org.betterx.bclib.api.v2.generator.BCLBiomeSource;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Publish the entire picker/map rebuild before any parallel biome sampling. */
@Pseudo
@Mixin(targets={"org.betterx.bclib.api.v2.generator.BCLibEndBiomeSource",
                "org.betterx.bclib.api.v2.generator.BCLibNetherBiomeSource"},remap=false)
public abstract class BclibSourceInit extends BCLBiomeSource {
    protected BclibSourceInit(long seed) { super(seed); }

    @Unique private volatile boolean expedition$sourceReady;

    @Inject(method="m_203407_(IIILnet/minecraft/world/level/biome/Climate$Sampler;)Lnet/minecraft/core/Holder;",
            at=@At("HEAD"),remap=false)
    private void expedition$publishSource(int x, int y, int z, Climate.Sampler sampler,
            CallbackInfoReturnable<Holder<Biome>> cir) {
        if (!expedition$sourceReady || !wasBound()) {
            synchronized (this) {
                if (!expedition$sourceReady || !wasBound()) {
                    // Original reload rebuilds pickers AND maps. Its own bound flag is
                    // set before tree rebuilding finishes and cannot publish readiness.
                    reloadBiomes(false);
                    expedition$sourceReady = wasBound();
                    if (expedition$sourceReady) {
                        System.out.println("[Expedition Worldgen] Published BCLib biome source after complete initialization: " + toShortString());
                    }
                }
            }
        }
    }
}
