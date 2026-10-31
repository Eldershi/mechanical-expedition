package expedition.maidguard.mixin;
import expedition.maidguard.WorldAgeGuard;
import net.minecraft.server.level.ServerLevel;
import net.minecraftforge.event.server.ServerStartedEvent;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Shared server callback: applies to dedicated and integrated servers. */
@Mixin(targets="com.github.yimeng261.maidspell.worldgen.StellarEndshoreFixedSpawn",remap=false)
public abstract class StellarEndshoreStartupGuard {
    @Inject(method="onServerStarted(Lnet/minecraftforge/event/server/ServerStartedEvent;)V",
        at=@At("HEAD"),cancellable=true,remap=false,require=1,allow=1)
    private static void expedition$protectExistingWorld(ServerStartedEvent event,CallbackInfo ci) {
        ServerLevel overworld=event.getServer().m_129783_();
        if(overworld!=null && WorldAgeGuard.existingWorld(overworld.m_46467_())) {
            WorldAgeGuard.blocked(overworld.m_46467_());
            ci.cancel();
        }
    }
}
