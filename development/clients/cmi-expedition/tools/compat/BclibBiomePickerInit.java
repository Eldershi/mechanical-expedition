package expedition.worldgen.mixin;

import net.minecraft.world.level.levelgen.WorldgenRandom;
import org.betterx.bclib.util.WeighTree;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Preserve BCLib's own weights while making first sampling safe before rebuild. */
@Pseudo
@Mixin(targets="org.betterx.bclib.api.v2.generator.BiomePicker",remap=false)
public abstract class BclibBiomePickerInit {
    @Shadow(remap=false) private WeighTree<?> tree;
    @Shadow(remap=false) public abstract void rebuild();
    // Publishes the original, non-volatile tree safely to subsequent sampler threads.
    @Unique private volatile boolean expedition$pickerReady;

    @Inject(method="getBiome(Lnet/minecraft/world/level/levelgen/WorldgenRandom;)Lorg/betterx/bclib/api/v2/generator/BiomePicker$ActualBiome;",
            at=@At("HEAD"),remap=false)
    private void expedition$initializePicker(WorldgenRandom random, CallbackInfoReturnable<?> cir) {
        if (!expedition$pickerReady) {
            synchronized (this) {
                if (!expedition$pickerReady) {
                    if (tree == null) {
                        rebuild();
                        System.out.println("[Expedition Worldgen] Rebuilt uninitialized BCLib BiomePicker before first sample");
                    }
                    expedition$pickerReady = true;
                }
            }
        }
    }
}
