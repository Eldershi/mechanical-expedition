package expedition.accessoryentry;

import com.aetherteam.aether.client.AetherKeys;
import com.aetherteam.aether.client.gui.component.inventory.AccessoryButton;
import io.wispforest.accessories.client.AccessoriesClient;
import java.util.List;
import net.blay09.mods.trashslot.client.LayoutManager;
import net.blay09.mods.trashslot.client.gui.layout.SimpleGuiContainerLayout;
import net.minecraft.client.KeyMapping;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.ImageButton;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.components.events.GuiEventListener;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.gui.screens.inventory.CreativeModeInventoryScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.network.chat.Component;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.bus.api.EventPriority;
import net.neoforged.bus.api.SubscribeEvent;
import net.neoforged.fml.ModList;
import net.neoforged.fml.common.EventBusSubscriber;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.RegisterMenuScreensEvent;
import net.neoforged.neoforge.network.PacketDistributor;
import net.neoforged.neoforge.client.event.ScreenEvent;
import org.lwjgl.glfw.GLFW;
import top.theillusivec4.curios.client.KeyRegistry;
import top.theillusivec4.curios.client.gui.CuriosButton;

@EventBusSubscriber(modid = AccessoryMenuMod.ID, value = Dist.CLIENT)
public final class AccessoryEntry {
    static final String TITLE = "expedition.accessory_entry.title";

    @SubscribeEvent
    static void registerScreen(RegisterMenuScreensEvent event) {
        event.register(AccessoryMenuMod.MENU.get(), AccessoryScreen::new);
        if (ModList.get().isLoaded("trashslot")) {
            LayoutManager.registerLayout(AccessoryScreen.class, SimpleGuiContainerLayout.DEFAULT_ENABLED);
        }
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    static void routeKeyBindings(ClientTickEvent.Pre event) {
        var client = Minecraft.getInstance();
        if (client.player == null || !client.isWindowActive()) {
            return;
        }
        boolean opened = consume(KeyRegistry.openCurios) | consume(AetherKeys.OPEN_ACCESSORY_INVENTORY);
        if (!net.minecraft.client.gui.screens.Screen.hasShiftDown()) {
            opened |= consume(AccessoriesClient.OPEN_SCREEN);
        }
        if (opened) {
            requestOpen();
        }
    }

    private static boolean consume(KeyMapping key) {
        if (key == null || !key.consumeClick()) {
            return false;
        }
        while (key.consumeClick()) {
            // Ignore repeated presses already queued for this tick.
        }
        return true;
    }

    private static void requestOpen() {
        var player = Minecraft.getInstance().player;
        if (player != null && player.inventoryMenu.getCarried().isEmpty()) {
            PacketDistributor.sendToServer(AccessoryMenuMod.OpenMenu.INSTANCE);
        }
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    static void install(ScreenEvent.Init.Post event) {
        if (!(event.getScreen() instanceof InventoryScreen)
                && !(event.getScreen() instanceof CreativeModeInventoryScreen)) {
            return;
        }
        for (GuiEventListener widget : List.copyOf(event.getListenersList())) {
            if (widget instanceof CuriosButton || widget instanceof AccessoryButton) {
                event.removeListener(widget);
            }
        }
        event.addListener(new EntryButton((AbstractContainerScreen<?>) event.getScreen()));
    }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    static void onMousePressed(ScreenEvent.MouseButtonPressed.Pre event) {
        if (event.getButton() != GLFW.GLFW_MOUSE_BUTTON_LEFT) {
            return;
        }
        for (GuiEventListener widget : event.getScreen().children()) {
            if (widget instanceof EntryButton entry && entry.clickInventory(event.getMouseX(), event.getMouseY())) {
                event.setCanceled(true);
                return;
            }
        }
    }

    private static final class EntryButton extends ImageButton {
        private final AbstractContainerScreen<?> inventory;

        EntryButton(AbstractContainerScreen<?> inventory) {
            super(0, 0, 10, 10, CuriosButton.BIG,
                button -> requestOpen(),
                Component.translatable(TITLE));
            this.inventory = inventory;
            setTooltip(Tooltip.create(Component.translatable(TITLE)));
            updatePosition();
        }

        private void updatePosition() {
            boolean creative = inventory instanceof CreativeModeInventoryScreen;
            active = !(inventory instanceof CreativeModeInventoryScreen screen) || screen.isInventoryOpen();
            setX(inventory.getGuiLeft() + (creative ? 96 : 27));
            setY(inventory.getGuiTop() + (creative ? 6 : 68));
        }

        boolean clickInventory(double x, double y) {
            if (inventory instanceof InventoryScreen survival && survival.width < 379
                    && survival.getRecipeBookComponent().isVisible()) {
                return false;
            }
            updatePosition();
            if (!mouseClicked(x, y, GLFW.GLFW_MOUSE_BUTTON_LEFT)) {
                return false;
            }
            inventory.setFocused(this);
            return true;
        }

        @Override
        public void renderWidget(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
            updatePosition();
            if (active) {
                super.renderWidget(graphics, mouseX, mouseY, delta);
            }
        }
    }
}
