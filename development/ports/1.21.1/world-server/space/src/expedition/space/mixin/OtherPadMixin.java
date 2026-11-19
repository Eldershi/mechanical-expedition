package expedition.space.mixin;

import com.thevortex.allthemodium.blocks.TeleportPad;
import expedition.space.SpaceLogistics;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = TeleportPad.class, remap = false)
abstract class OtherPadMixin {
    @Shadow
    private int config() { throw new AssertionError(); }

    @Inject(method = "transferPlayer", at = @At("HEAD"), cancellable = true)
    private void lunarAccess(ServerPlayer player, BlockPos source, CallbackInfo callback) {
        if (player.level().dimension().equals(Level.NETHER)
            && SpaceLogistics.isOther(TeleportPad.getPartner(Level.NETHER, config()))
            && !SpaceLogistics.mayUseOtherPad(player)) {
            player.displayClientMessage(Component.translatable("expedition_space.pad_locked"), true);
            callback.cancel();
        }
    }
}
