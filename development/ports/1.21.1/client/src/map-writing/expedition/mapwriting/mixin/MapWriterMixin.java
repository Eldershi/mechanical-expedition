package expedition.mapwriting.mixin;

import expedition.mapwriting.MapWritingOptions;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import xaero.map.MapWriter;
import xaero.map.gui.GuiMap;

@Mixin(value = MapWriter.class, remap = false)
abstract class MapWriterMixin {
    @Inject(method = "onRender", at = @At("HEAD"), cancellable = true)
    private void expedition$pauseBackgroundWrites(CallbackInfo callback) {
        var client = Minecraft.getInstance();
        if (MapWritingOptions.PAUSE_SINGLEPLAYER_BACKGROUND && client.hasSingleplayerServer()
            && !(client.screen instanceof GuiMap)) {
            callback.cancel();
        }
    }
}
