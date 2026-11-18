package expedition.ftbteamscompat.mixin;

import java.util.UUID;
import net.minecraft.client.Minecraft;
import net.minecraft.client.User;
import net.minecraft.client.multiplayer.ClientPacketListener;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Use the server-accepted UUID when resolving the local FTB Teams record. */
@Mixin(targets = "dev.ftb.mods.ftbteams.data.ClientTeamManagerImpl", remap = false)
abstract class ClientIdentityMixin {
    @Redirect(method = "initSelfDetails(Ljava/util/UUID;)V",
        at = @At(value = "INVOKE", target = "Lnet/minecraft/client/User;getProfileId()Ljava/util/UUID;"),
        require = 1, allow = 1)
    private UUID expedition$connectedIdentity(User launcherUser) {
        ClientPacketListener connection = Minecraft.getInstance().getConnection();
        UUID acceptedId = connection == null ? null : connection.getLocalGameProfile().getId();
        return acceptedId == null ? launcherUser.getProfileId() : acceptedId;
    }
}
