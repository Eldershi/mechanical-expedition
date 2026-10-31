package expedition.ponderui.mixin;

import expedition.ponderui.SpellPonderCatalog;
import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value=Minecraft.class,remap=false)
public abstract class SpellPonderClientSync {
    @Inject(method="m_91398_",at=@At("TAIL"))
    private void expedition$refreshSchools(CallbackInfo ci) {SpellPonderCatalog.refreshAfterConfigSync();}
}
