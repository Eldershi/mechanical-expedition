package expedition.fireworks.mixin;

import expedition.fireworks.HarmlessVariantFireworks;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "com.github.alexmodguy.alexscaves.server.entity.living.GumbeeperEntity", remap = false)
public abstract class GumbeeperFireworkMixin {
    @Shadow(remap = false) public abstract boolean isCharged();

    // First isCharged call is inside the finished (20 tick) detonation branch,
    // immediately before spawning the damaging ring of gumball projectiles.
    @Inject(method = "m_8119_()V", at = @At(value = "INVOKE",
            target = "Lcom/github/alexmodguy/alexscaves/server/entity/living/GumbeeperEntity;isCharged()Z",
            ordinal = 0, remap = false), cancellable = true, remap = false)
    private void expedition$firework(CallbackInfo callback) {
        if (HarmlessVariantFireworks.convert((Entity) (Object) this, isCharged())) callback.cancel();
    }
}
