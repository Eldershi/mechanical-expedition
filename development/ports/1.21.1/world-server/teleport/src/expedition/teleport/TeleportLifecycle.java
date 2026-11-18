package expedition.teleport;

import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.server.ServerStoppingEvent;

@Mod("expedition_teleport_fix")
public final class TeleportLifecycle {
    public TeleportLifecycle() {
        NeoForge.EVENT_BUS.addListener(this::onStopping);
    }

    private void onStopping(ServerStoppingEvent event) {
        AsyncTeleportPreparation.stop(event.getServer());
    }
}
