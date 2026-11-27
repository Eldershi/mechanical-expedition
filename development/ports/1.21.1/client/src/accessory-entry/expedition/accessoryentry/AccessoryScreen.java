package expedition.accessoryentry;

import io.wispforest.accessories.menu.AccessoriesInternalSlot;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.screens.inventory.EffectRenderingInventoryScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.Slot;
import org.lwjgl.glfw.GLFW;
import top.theillusivec4.curios.common.inventory.CurioSlot;

final class AccessoryScreen extends EffectRenderingInventoryScreen<AccessoryMenu> {
    private static final String TEXT = "expedition.accessory_entry.";
    private final Button[][] pageButtons = new Button[AccessoryMenu.Group.values().length][2];
    private Button view;

    AccessoryScreen(AccessoryMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        imageWidth = 272;
        imageHeight = 215;
        inventoryLabelY = AccessoryMenu.INVENTORY_Y - 11;
    }

    @Override
    protected void init() {
        super.init();
        view = addRenderableWidget(Button.builder(Component.empty(), button -> {
            menu.toggleCosmetics();
            refreshControls();
        }).bounds(leftPos + 106, topPos + 4, 63, 17).build());
        for (var group : AccessoryMenu.Group.values()) {
            pageButtons[group.ordinal()][0] = addRenderableWidget(pageButton(group, -1, 131));
            pageButtons[group.ordinal()][1] = addRenderableWidget(pageButton(group, 1, 153));
        }
        refreshControls();
    }

    @Override
    protected void containerTick() {
        super.containerTick();
        if (!menu.layoutMatches() && minecraft != null && minecraft.player != null) {
            minecraft.player.closeContainer();
            minecraft.player.displayClientMessage(Component.translatable(TEXT + "syncing"), true);
        }
    }

    private Button pageButton(AccessoryMenu.Group group, int delta, int x) {
        return Button.builder(Component.literal(delta < 0 ? "‹" : "›"), button -> {
            menu.changePage(group, delta);
            refreshControls();
        }).bounds(leftPos + x, topPos + group.y - 15, 15, 13).build();
    }

    private void refreshControls() {
        view.setMessage(Component.translatable(TEXT + (menu.cosmetics() ? "cosmetic" : "equipped")));
        view.setTooltip(Tooltip.create(Component.translatable(TEXT + "switch_view")));
        for (var group : AccessoryMenu.Group.values()) {
            Button[] buttons = pageButtons[group.ordinal()];
            buttons[0].visible = buttons[1].visible = menu.pages(group) > 1;
            buttons[0].active = menu.page(group) > 0;
            buttons[1].active = menu.page(group) + 1 < menu.pages(group);
        }
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float partialTick, int mouseX, int mouseY) {
        graphics.fill(leftPos, topPos, leftPos + imageWidth, topPos + imageHeight, 0xff31241c);
        graphics.fill(leftPos + 2, topPos + 2, leftPos + imageWidth - 2, topPos + imageHeight - 2, 0xffd9c3a7);
        graphics.fill(leftPos + 177, topPos + 8, leftPos + 179, topPos + imageHeight - 8, 0xffa98c6b);
        graphics.fill(leftPos + 205, topPos + 23, leftPos + 264, topPos + 91, 0xff6c513a);
        if (minecraft != null && minecraft.player != null) {
            InventoryScreen.renderEntityInInventoryFollowsMouse(graphics, leftPos + 206, topPos + 24,
                leftPos + 263, topPos + 90, 29, 0.0625f, mouseX, mouseY, minecraft.player);
        }
        for (Slot slot : menu.slots) {
            if (slot.isActive()) {
                int x = leftPos + slot.x - 1;
                int y = topPos + slot.y - 1;
                graphics.fill(x, y, x + 18, y + 18, 0xff6c513a);
                graphics.fill(x + 1, y + 1, x + 17, y + 17, 0xffa98c6b);
            }
        }
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        super.renderLabels(graphics, mouseX, mouseY);
        graphics.drawString(font, Component.translatable(TEXT + "curios"), 8, 25, 0x403020, false);
        graphics.drawString(font, Component.translatable(TEXT + "accessories"), 8, 75, 0x403020, false);
        graphics.drawString(font, Component.translatable("container.crafting"), 185, 122, 0x403020, false);
        graphics.drawString(font, "→", 224, 145, 0x403020, false);
        for (var group : AccessoryMenu.Group.values()) {
            if (menu.pages(group) > 1) {
                String page = (menu.page(group) + 1) + "/" + menu.pages(group);
                graphics.drawString(font, page, 127 - font.width(page), group.y - 11, 0x403020, false);
            }
        }
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
        super.render(graphics, mouseX, mouseY, delta);
        renderTooltip(graphics, mouseX, mouseY);
    }

    @Override
    protected void renderTooltip(GuiGraphics graphics, int mouseX, int mouseY) {
        super.renderTooltip(graphics, mouseX, mouseY);
        if (hoveredSlot == null || hoveredSlot.hasItem() || !menu.getCarried().isEmpty()) {
            return;
        }
        if (hoveredSlot instanceof AccessoriesInternalSlot slot) {
            graphics.renderComponentTooltip(font, slot.getTooltipData(), mouseX, mouseY);
        } else if (hoveredSlot instanceof CurioSlot slot) {
            graphics.renderTooltip(font, Component.translatable("curios.identifier." + slot.getIdentifier()), mouseX, mouseY);
        }
    }

    @Override
    public boolean mouseClicked(double mouseX, double mouseY, int button) {
        if (button == GLFW.GLFW_MOUSE_BUTTON_RIGHT && hasShiftDown() && hoveredSlot != null
                && hoveredSlot.isActive() && isHovering(hoveredSlot.x, hoveredSlot.y, 16, 16, mouseX, mouseY)
                && menu.getCarried().isEmpty() && !menu.cosmetics()
                && (hoveredSlot instanceof AccessoriesInternalSlot
                    || hoveredSlot instanceof CurioSlot slot && slot.canToggleRender())) {
            if (minecraft != null && minecraft.gameMode != null) {
                minecraft.gameMode.handleInventoryButtonClick(menu.containerId, hoveredSlot.index);
            }
            return true;
        }
        return super.mouseClicked(mouseX, mouseY, button);
    }
}
