package expedition.toolplanner;

import modernmods.modernfoundry.library.materials.MaterialRegistry;
import modernmods.modernfoundry.tables.client.inventory.TinkerStationScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.network.chat.Component;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.common.NeoForge;

@Mod(value = "expedition_tool_planner", dist = Dist.CLIENT)
public final class ExpeditionToolPlanner {
    public ExpeditionToolPlanner() {
        NeoForge.EVENT_BUS.addListener(ExpeditionToolPlanner::addPlanner);
    }

    private static void addPlanner(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof TinkerStationScreen station)) return;
        Minecraft client = Minecraft.getInstance();
        Button button = Button.builder(Component.translatable("expedition.planner.title"), clicked -> {
            if (MaterialRegistry.isFullyLoaded()) client.setScreen(new ToolPlannerScreen(station));
        }).bounds(station.width - 123, 6, 117, 20).build();
        event.addListener(button);
    }
}
