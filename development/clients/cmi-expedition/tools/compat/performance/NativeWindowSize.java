package expedition.performance.client;
import com.mojang.blaze3d.platform.Window;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;
@Mixin(value = Window.class, remap = false)
public interface NativeWindowSize {
    @Accessor(value = "f_85361_", remap = false) int expedition$nativeWidth();
    @Accessor(value = "f_85362_", remap = false) int expedition$nativeHeight();
}
