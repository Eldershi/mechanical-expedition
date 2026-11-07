package expedition.ftbteamscompat.mixin;

import com.mojang.authlib.GameProfile;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientPacketListener;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import java.util.UUID;

/** Resolve FTB's local player using the identity accepted by the connected server. */
@Mixin(targets = "dev.ftb.mods.ftbteams.data.ClientTeamManagerImpl", remap = false)
public abstract class ClientIdentityMixin {
    @Redirect(method = "initSelfDetails", at = @At(value = "INVOKE",
        target = "Lcom/mojang/authlib/GameProfile;getId()Ljava/util/UUID;"), require = 1)
    private UUID expedition$connectedIdentity(GameProfile launcherProfile) {
        ClientPacketListener connection = Minecraft.m_91087_().m_91403_();
        return connection == null ? launcherProfile.getId() : connection.m_105144_().getId();
    }
}
