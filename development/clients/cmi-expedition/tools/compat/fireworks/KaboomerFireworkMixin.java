package expedition.fireworks.mixin;

import expedition.fireworks.HarmlessVariantFireworks;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "com.yellowbrossproductions.illageandspillage.entities.KaboomerEntity", remap = false)
public abstract class KaboomerFireworkMixin {
    @Inject(method = "explode()V", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$firework(CallbackInfo callback) {
        if (HarmlessVariantFireworks.convert((Entity) (Object) this, false)) callback.cancel();
    }
}
