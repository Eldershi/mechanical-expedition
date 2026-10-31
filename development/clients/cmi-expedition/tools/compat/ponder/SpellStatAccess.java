package expedition.ponderui.mixin;

import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

@Mixin(targets="com.p1nero.iss_ponder.client.SpellPreviewScreen$StatEntry", remap=false)
public interface SpellStatAccess {
    @Accessor("label") Component expedition$label();
    @Accessor("value") Component expedition$value();
    @Accessor("color") int expedition$color();
}
