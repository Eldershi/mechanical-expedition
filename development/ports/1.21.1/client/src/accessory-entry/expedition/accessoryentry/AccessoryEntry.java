package expedition.accessoryentry;

import com.aetherteam.aether.client.gui.component.inventory.AccessoryButton;
import io.wispforest.accessories.client.AccessoriesClient;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.ImageButton;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.components.events.GuiEventListener;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.network.chat.Component;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.common.NeoForge;
import org.lwjgl.glfw.GLFW;
import top.theillusivec4.curios.client.gui.CuriosButton;

@Mod(value = "expedition_accessory_entry", dist = Dist.CLIENT)
public final class AccessoryEntry {
    private static final String TITLE = "expedition.accessory_entry.title";

    public AccessoryEntry() {
        NeoForge.EVENT_BUS.addListener(EventPriority.LOWEST, AccessoryEntry::install);
        NeoForge.EVENT_BUS.addListener(AccessoryEntry::closeOnEscape);
    }

    private static void install(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof InventoryScreen)
                && !(event.getScreen() instanceof CreativeModeInventoryScreen)) {
            return;
        }

        List<Destination> destinations = new ArrayList<>();
        for (GuiEventListener widget : List.copyOf(event.getListenersList())) {
            if (widget instanceof CuriosButton curios) {
                destinations.addFirst(new Destination("curios", curios::onPress));
                event.removeListener(curios);
            } else if (widget instanceof AccessoryButton aether) {
                destinations.add(new Destination("aether", aether::onPress));
                event.removeListener(aether);
            }
        }
        destinations.add(new Destination("accessories", AccessoriesClient::attemptToOpenScreen));

        EntryButton entry = new EntryButton((AbstractContainerScreen<?>) event.getScreen());
        event.addListener(entry);
        for (Destination destination : destinations) {
            var row = new DestinationButton(entry, destination, entry.rows.size());
            entry.rows.add(row);
            event.addListener(row);
        }
    }

    private static void closeOnEscape(ScreenEvent.KeyPressed.Pre event) {
        if (event.getKeyCode() != GLFW.GLFW_KEY_ESCAPE) {
            return;
        }
        for (GuiEventListener widget : event.getScreen().children()) {
            if (widget instanceof EntryButton entry && entry.expanded) {
                entry.setExpanded(false);
                event.getScreen().setFocused(entry);
                event.setCanceled(true);
                return;
            }
        }
    }

    private record Destination(String key, Runnable open) {}

    private static final class EntryButton extends ImageButton {
        private final AbstractContainerScreen<?> inventory;
        private final List<DestinationButton> rows = new ArrayList<>();
        private boolean expanded;

        EntryButton(AbstractContainerScreen<?> inventory) {
            super(0, 0, 10, 10, CuriosButton.BIG, button -> {}, Component.translatable(TITLE));
            this.inventory = inventory;
            setTooltip(Tooltip.create(Component.translatable(TITLE)));
            updatePosition();
        }

        @Override
        public void onPress() {
            setExpanded(!expanded);
        }

        void setExpanded(boolean expanded) {
            this.expanded = expanded;
            for (DestinationButton row : rows) {
                row.visible = expanded;
                row.active = expanded;
            }
        }

        private void updatePosition() {
            boolean creative = inventory instanceof CreativeModeInventoryScreen;
            setX(inventory.getGuiLeft() + (creative ? 96 : 66));
            setY(inventory.getGuiTop() + (creative ? 6 : 8));
        }

        @Override
        public void renderWidget(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
            updatePosition();
            active = !(inventory instanceof CreativeModeInventoryScreen creative) || creative.isInventoryOpen();
            if (!active) {
                setExpanded(false);
                return;
            }
            super.renderWidget(graphics, mouseX, mouseY, delta);
        }
    }

    private static final class DestinationButton extends Button {
        private final EntryButton entry;
        private final int row;

        DestinationButton(EntryButton entry, Destination destination, int row) {
            super(entry.getX(), entry.getY(), 98, 18,
                Component.translatable("expedition.accessory_entry." + destination.key()),
                button -> {
                    entry.setExpanded(false);
                    destination.open().run();
                }, DEFAULT_NARRATION);
            this.entry = entry;
            this.row = row;
            visible = false;
            active = false;
        }

        @Override
        public void renderWidget(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
            setX(entry.getX() - 18);
            setY(entry.getY() + 12 + row * 19);
            graphics.pose().pushPose();
            graphics.pose().translate(0, 0, 450);
            super.renderWidget(graphics, mouseX, mouseY, delta);
            graphics.pose().popPose();
        }
    }
}
