package expedition.accessoryentry;

import io.wispforest.accessories.menu.AccessoriesInternalSlot;
import net.blay09.mods.balm.mixin.SlotAccessor;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.components.ImageButton;
import net.minecraft.client.gui.components.Tooltip;
import net.minecraft.client.gui.screens.inventory.EffectRenderingInventoryScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import net.minecraft.client.gui.screens.recipebook.RecipeBookComponent;
import net.minecraft.client.gui.screens.recipebook.RecipeUpdateListener;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.inventory.ClickType;
import net.minecraft.world.inventory.Slot;
import net.neoforged.neoforge.network.PacketDistributor;
import org.lwjgl.glfw.GLFW;
import org.violetmoon.quark.base.network.message.SortInventoryMessage;
import org.violetmoon.quark.content.management.client.screen.widgets.MiniInventoryButton;
import top.theillusivec4.curios.api.client.ICuriosScreen;
import top.theillusivec4.curios.client.gui.CosmeticButton;
import top.theillusivec4.curios.common.inventory.CurioSlot;

final class AccessoryScreen extends EffectRenderingInventoryScreen<AccessoryMenu>
        implements ICuriosScreen, RecipeUpdateListener {
    private static final ResourceLocation INVENTORY = ResourceLocation.withDefaultNamespace("textures/gui/container/inventory.png");
    private static final ResourceLocation CURIOS = ResourceLocation.fromNamespaceAndPath("curios", "textures/gui/curios/inventory.png");
    private static final int COLUMN = AccessoryMenu.CELL;
    private static final int EDGE = AccessoryMenu.INSET;
    private static final int INV_WIDTH = AccessoryMenu.INVENTORY_WIDTH;
    private static final int INV_HEIGHT = AccessoryMenu.INVENTORY_HEIGHT;
    private final RecipeBookComponent recipeBook = new RecipeBookComponent();
    private ImageButton bookButton;
    private ImageButton cosmeticsButton;
    private MiniInventoryButton sortButton;
    private int columns;
    private int rows;
    private int inventoryX;
    private int placedInventoryX;
    private boolean compactBook;

    AccessoryScreen(AccessoryMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
        imageHeight = INV_HEIGHT;
    }

    @Override
    protected void init() {
        columns = Math.clamp((width - INV_WIDTH - 2 * EDGE - 2) / COLUMN, 1, AccessoryMenu.PREFERRED_COLUMNS);
        menu.setViewport(columns, AccessoryMenu.PREFERRED_ROWS);
        rows = Math.clamp(menu.rowCount(), 1, AccessoryMenu.PREFERRED_ROWS);
        menu.setViewport(columns, rows);
        inventoryX = 2 * EDGE + columns * COLUMN + 2;
        imageWidth = inventoryX + INV_WIDTH;
        super.init();

        compactBook = width < 379;
        recipeBook.init(width, height, minecraft, compactBook, menu);
        addWidget(recipeBook);
        bookButton = addRenderableWidget(new ImageButton(0, 0, 20, 18,
            RecipeBookComponent.RECIPE_BUTTON_SPRITES, button -> {
                recipeBook.toggleVisibility();
                placeControls();
            }));
        bookButton.setTooltip(Tooltip.create(Component.translatable("gui.recipebook.toggleRecipes")));
        if (menu.hasCosmetics()) {
            cosmeticsButton = addRenderableWidget(new ImageButton(0, 0, 20, 17, CosmeticButton.OFF,
                    button -> menu.toggleCosmetics()) {
                @Override
                public void renderWidget(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
                    var sprites = menu.cosmetics() ? CosmeticButton.ON : CosmeticButton.OFF;
                    graphics.blitSprite(sprites.get(isActive(), isHoveredOrFocused()),
                        getX(), getY(), getWidth(), getHeight());
                }
            });
            cosmeticsButton.setTooltip(Tooltip.create(Component.translatable("gui.curios.toggle.cosmetics")));
        }
        sortButton = addRenderableWidget(new MiniInventoryButton(this, 0, 162, -14,
            Component.translatable("quark.gui.button.sort"),
            button -> PacketDistributor.sendToServer(new SortInventoryMessage(true))));
        placeControls();
    }

    boolean ownsSortButton(MiniInventoryButton button) {
        return sortButton == button;
    }

    private void placeControls() {
        boolean showingBook = recipeBook.isVisible();
        leftPos = showingBook ? recipeBook.updateScreenPosition(width, INV_WIDTH) - inventoryX
            : (width - imageWidth) / 2;
        menu.setAccessoriesVisible(!showingBook);
        bookButton.setPosition(getGuiLeft() + 104, topPos + 61);
        if (cosmeticsButton != null) {
            cosmeticsButton.setPosition(getGuiLeft() - 27, topPos - 18);
            cosmeticsButton.visible = !showingBook;
        }
        positionSlots();
    }

    private void positionSlots() {
        for (Slot slot : menu.slots) {
            if (slot.index < AccessoryMenu.ACCESSORY_START) {
                ((SlotAccessor) slot).setX(slot.x + inventoryX - placedInventoryX);
            } else if (menu.layoutMatches()) {
                int cell = menu.accessoryCell(slot.index);
                ((SlotAccessor) slot).setX(EDGE + 1 + cell % columns * COLUMN);
                ((SlotAccessor) slot).setY(EDGE + 1 + (cell / columns - menu.firstRow()) * COLUMN);
            }
        }
        placedInventoryX = inventoryX;
    }

    @Override
    public int getGuiLeft() {
        return leftPos + inventoryX;
    }

    @Override
    protected void containerTick() {
        super.containerTick();
        if (!menu.layoutMatches() && minecraft.player != null) {
            minecraft.player.closeContainer();
            minecraft.player.displayClientMessage(Component.translatable("expedition.accessory_entry.syncing"), true);
            return;
        }
        recipeBook.tick();
    }

    @Override
    protected void renderBg(GuiGraphics graphics, float delta, int mouseX, int mouseY) {
        int invLeft = getGuiLeft();
        graphics.blit(INVENTORY, invLeft, topPos, 0, 0, INV_WIDTH, INV_HEIGHT);
        InventoryScreen.renderEntityInInventoryFollowsMouse(graphics, invLeft + 26, topPos + 8,
            invLeft + 75, topPos + 78, 30, 0.0625f, mouseX, mouseY, minecraft.player);
        if (recipeBook.isVisible()) return;

        int body = EDGE + rows * COLUMN;
        drawColumn(graphics, leftPos, 91, EDGE, body);
        for (int col = 0; col < columns; col++) {
            drawColumn(graphics, leftPos + EDGE + col * COLUMN, 98, COLUMN, body);
        }
        drawColumn(graphics, leftPos + inventoryX - EDGE - 2, 116, EDGE, body);
        if (cosmeticsButton != null) {
            graphics.blit(CURIOS, invLeft - 31, topPos - 23, 32, 0, 28, 24);
        }
        int first = menu.firstRow() * columns;
        int end = Math.min(menu.accessoryCount(), first + rows * columns);
        for (int cell = first; cell < end; cell++) {
            graphics.blit(CURIOS, leftPos + EDGE + cell % columns * COLUMN,
                topPos + EDGE + (cell / columns - menu.firstRow()) * COLUMN, 7, 7, COLUMN, COLUMN);
        }
    }

    private void drawColumn(GuiGraphics graphics, int x, int u, int width, int body) {
        graphics.blit(CURIOS, x, topPos, u, 0, width, body);
        graphics.blit(CURIOS, x, topPos + body, u, 159, width, EDGE);
    }

    @Override
    protected void renderLabels(GuiGraphics graphics, int mouseX, int mouseY) {
        graphics.drawString(font, Component.translatable("container.crafting"), inventoryX + 97, 8, 0x404040, false);
    }

    @Override
    public void render(GuiGraphics graphics, int mouseX, int mouseY, float delta) {
        if (compactBook && recipeBook.isVisible()) {
            renderBackground(graphics, mouseX, mouseY, delta);
            recipeBook.render(graphics, mouseX, mouseY, delta);
        } else {
            super.render(graphics, mouseX, mouseY, delta);
            if (recipeBook.isVisible()) {
                recipeBook.render(graphics, mouseX, mouseY, delta);
                recipeBook.renderGhostRecipe(graphics, leftPos, topPos, false, delta);
            } else if (!menu.cosmetics()) {
                for (Slot slot : menu.slots) {
                    if (canToggle(slot)) {
                        graphics.blit(CURIOS, leftPos + slot.x + 10, topPos + slot.y,
                            menu.renderEnabled(slot) ? 76 : 84, 1, 6, 6);
                    }
                }
            }
            renderTooltip(graphics, mouseX, mouseY);
        }
        recipeBook.renderTooltip(graphics, leftPos, topPos, mouseX, mouseY);
    }

    private static boolean canToggle(Slot slot) {
        return slot.isActive() && (slot instanceof AccessoriesInternalSlot
            || slot instanceof CurioSlot curio && curio.canToggleRender());
    }

    @Override
    protected void renderTooltip(GuiGraphics graphics, int mouseX, int mouseY) {
        super.renderTooltip(graphics, mouseX, mouseY);
        if (hoveredSlot == null || hoveredSlot.hasItem() || !menu.getCarried().isEmpty()) return;
        if (hoveredSlot instanceof AccessoriesInternalSlot slot) {
            graphics.renderComponentTooltip(font, slot.getTooltipData(), mouseX, mouseY);
        } else if (hoveredSlot instanceof CurioSlot slot) {
            graphics.renderTooltip(font, Component.translatable("curios.identifier." + slot.getIdentifier()), mouseX, mouseY);
        }
    }

    @Override
    public boolean mouseScrolled(double x, double y, double horizontal, double vertical) {
        if (!recipeBook.isVisible() && x >= leftPos && x < getGuiLeft() - 2
                && y >= topPos && y < topPos + EDGE * 2 + rows * COLUMN && menu.rowCount() > rows) {
            menu.scrollRows(vertical < 0 ? 1 : vertical > 0 ? -1 : 0);
            positionSlots();
            return true;
        }
        return super.mouseScrolled(x, y, horizontal, vertical);
    }

    @Override
    public boolean mouseClicked(double x, double y, int button) {
        if (recipeBook.mouseClicked(x, y, button)) {
            setFocused(recipeBook);
            placeControls();
            return true;
        }
        if (compactBook && recipeBook.isVisible()) return true;
        if (hoveredSlot != null && !menu.cosmetics() && menu.getCarried().isEmpty() && canToggle(hoveredSlot)) {
            boolean dot = button == GLFW.GLFW_MOUSE_BUTTON_LEFT
                && isHovering(hoveredSlot.x + 10, hoveredSlot.y, 6, 6, x, y);
            boolean shortcut = button == GLFW.GLFW_MOUSE_BUTTON_RIGHT && hasShiftDown()
                && isHovering(hoveredSlot.x, hoveredSlot.y, 16, 16, x, y);
            if (dot || shortcut) {
                minecraft.gameMode.handleInventoryButtonClick(menu.containerId, hoveredSlot.index);
                return true;
            }
        }
        return super.mouseClicked(x, y, button);
    }

    @Override
    public boolean keyPressed(int key, int scanCode, int modifiers) {
        if (recipeBook.keyPressed(key, scanCode, modifiers)) {
            placeControls();
            return true;
        }
        return super.keyPressed(key, scanCode, modifiers);
    }

    @Override
    protected boolean hasClickedOutside(double x, double y, int left, int top, int button) {
        return super.hasClickedOutside(x, y, left, top, button)
            && recipeBook.hasClickedOutside(x, y, getGuiLeft(), top, INV_WIDTH, INV_HEIGHT, button);
    }

    @Override
    protected void slotClicked(Slot slot, int id, int button, ClickType type) {
        super.slotClicked(slot, id, button, type);
        recipeBook.slotClicked(slot);
    }

    @Override
    public void recipesUpdated() {
        recipeBook.recipesUpdated();
    }

    @Override
    public RecipeBookComponent getRecipeBookComponent() {
        return recipeBook;
    }
}
