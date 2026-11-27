package expedition.siftcompat.mixin;

import com.bawnorton.mixinsquared.TargetHandler;
import mielon.thesift.map.SiftMapSampling;
import mielon.thesift.map.SiftMapStorage;
import net.minecraft.world.item.MapItem;
import net.minecraft.world.level.saveddata.maps.MapItemSavedData;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = MapItem.class, priority = 1500)
abstract class CivilMapMixin {
    // Sift's sampled layer uses the original write path when a custom pixel changes.
    @TargetHandler(mixin = "civil.mixin.CivilMapItemUpdateTintMixin",
                   name = "civil$tintOnVanillaUpdateColor")
    @Inject(method = "@MixinSquared:Handler", at = @At("HEAD"), cancellable = true, remap = false)
    private void expedition$writeSiftPixel(MapItemSavedData data, int x, int y, byte color,
                                          CallbackInfoReturnable<Boolean> result) {
        SiftMapStorage storage = (SiftMapStorage) data;
        if (storage.theSift$colors().set(x, y, SiftMapSampling.take())) {
            data.setColor(x, y, color);
            result.setReturnValue(true);
        }
    }
}
