package expedition.ponderui.mixin;

import net.createmod.ponder.foundation.PonderScene;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(targets="com.p1nero.iss_ponder.client.PreviewProjection",remap=false)
public interface PreviewProjectionAccess {
    @Accessor("scene") static PonderScene expedition$scene() {throw new AssertionError();}
    @Accessor("zoom") static float expedition$zoom() {throw new AssertionError();}
}
