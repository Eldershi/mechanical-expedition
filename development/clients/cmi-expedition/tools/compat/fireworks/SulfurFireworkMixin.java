package expedition.fireworks.mixin;

import expedition.fireworks.HarmlessVariantFireworks;
import net.minecraft.world.entity.monster.Creeper;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "earth.terrarium.adastra.common.entities.mob.SulfurCreeper", remap = false)
public abstract class SulfurFireworkMixin {
    @Inject(method = "explodeCreeper()V", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$firework(CallbackInfo callback) {
        if (HarmlessVariantFireworks.convert((Creeper) (Object) this)) callback.cancel();
    }
}
