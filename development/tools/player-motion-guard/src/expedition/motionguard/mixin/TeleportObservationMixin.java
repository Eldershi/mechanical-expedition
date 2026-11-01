package expedition.motionguard.mixin;

import expedition.motionguard.diagnostics.DiagnosticsService;
import java.util.Set;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.world.entity.RelativeMovement;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Records targets and relative flags without changing teleport behavior. */
@Mixin(value=ServerGamePacketListenerImpl.class,remap=false)
public abstract class TeleportObservationMixin {
    @Inject(method="m_9780_(DDDFFLjava/util/Set;)V",at=@At("HEAD"),require=1,allow=1,remap=false)
    private void expedition$recordTeleport(double x,double y,double z,float yaw,float pitch,
                                          Set<RelativeMovement> flags,CallbackInfo ci) {
        DiagnosticsService.teleport(((ServerGamePacketListenerImpl)(Object)this).f_9743_,x,y,z,yaw,pitch,flags);
    }
}
