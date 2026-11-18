package expedition.islandrail;

import net.neoforged.fml.common.Mod;

@Mod("expedition_island_rail_transfer")
public final class IslandRailTransfer {
    public IslandRailTransfer() {
        new IslandRailRebuild();
        new IslandBridgeTransfer();
    }
}
