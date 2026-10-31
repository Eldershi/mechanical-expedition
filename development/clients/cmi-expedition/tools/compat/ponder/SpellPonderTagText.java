package expedition.ponderui.mixin;

import expedition.ponderui.SpellPonderCatalog;
import net.createmod.ponder.foundation.PonderTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Dynamic add-on schools use their own translated name without generated lang keys. */
@Mixin(value=PonderTag.class,remap=false)
public abstract class SpellPonderTagText {
    @Shadow public abstract ResourceLocation getId();
    @Inject(method="getTitle",at=@At("HEAD"),cancellable=true)
    private void expedition$schoolTitle(CallbackInfoReturnable<String> ci) {
        var school=SpellPonderCatalog.school(getId());if(school!=null)ci.setReturnValue(school.title());
    }
    @Inject(method="getDescription",at=@At("HEAD"),cancellable=true)
    private void expedition$schoolDescription(CallbackInfoReturnable<String> ci) {
        var school=SpellPonderCatalog.school(getId());if(school!=null)
            ci.setReturnValue(Component.m_237110_("gui.expedition_ponder_ui.school_description",school.spells().size()).getString());
    }
}
