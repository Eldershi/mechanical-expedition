package expedition.ponderui.mixin;

import expedition.ponderui.SpellPonderCatalog;
import net.createmod.ponder.foundation.PonderIndex;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value=PonderIndex.class,remap=false)
public abstract class SpellPonderIndexBridge {
    @Unique private static boolean expedition$registered;
    @Inject(method="registerAll",at=@At("HEAD"))
    private static void expedition$registerSchools(CallbackInfo ci) {
        if(!expedition$registered) {expedition$registered=true;PonderIndex.addPlugin(new SpellPonderCatalog());}
    }
}
