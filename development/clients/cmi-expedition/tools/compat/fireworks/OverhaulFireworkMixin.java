package expedition.fireworks.mixin;

import expedition.fireworks.HarmlessVariantFireworks;
import net.minecraft.world.entity.monster.Creeper;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "tech.thatgravyboat.creeperoverhaul.common.entity.base.BaseCreeper", remap = false)
public abstract class OverhaulFireworkMixin {
    @Inject(method = "explode()V", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$firework(CallbackInfo callback) {
        if (HarmlessVariantFireworks.convert((Creeper) (Object) this)) callback.cancel();
    }
}
