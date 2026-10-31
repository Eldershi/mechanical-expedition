package expedition.fireworks.mixin;

import expedition.fireworks.HarmlessVariantFireworks;
import net.minecraft.world.entity.Entity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(targets = "net.miauczel.legendary_monsters.entity.AnimatedMonster.Mobs.RuinedPyramid.BomberEntity", remap = false)
public abstract class BomberFireworkMixin {
    @Shadow(remap = false) public abstract boolean isPowered();

    @Inject(method = "explodeCreeper()V", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$firework(CallbackInfo callback) {
        if (HarmlessVariantFireworks.convert((Entity) (Object) this, isPowered())) callback.cancel();
    }
}
