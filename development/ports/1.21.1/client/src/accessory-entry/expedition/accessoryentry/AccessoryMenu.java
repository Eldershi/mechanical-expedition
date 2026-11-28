package expedition.accessoryentry;

import com.aetherteam.aether.mixin.mixins.common.accessor.CraftingMenuAccessor;
import io.wispforest.accessories.api.AccessoriesCapability;
import io.wispforest.accessories.api.AccessoriesContainer;
import io.wispforest.accessories.menu.AccessoriesInternalSlot;
import io.wispforest.accessories.networking.server.SyncCosmeticToggle;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.Container;
import net.minecraft.world.SimpleContainer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.entity.player.StackedContents;
import net.minecraft.world.inventory.RecipeBookMenu;
import net.minecraft.world.inventory.RecipeBookType;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.inventory.ResultContainer;
import net.minecraft.world.inventory.ResultSlot;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.inventory.TransientCraftingContainer;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.neoforged.neoforge.network.PacketDistributor;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.type.ISlotType;
import top.theillusivec4.curios.api.type.inventory.ICurioStacksHandler;
import top.theillusivec4.curios.common.inventory.CurioSlot;
import top.theillusivec4.curios.common.network.server.sync.SPacketSyncRender;

final class AccessoryMenu extends RecipeBookMenu<CraftingInput, CraftingRecipe> {
    static final int INVENTORY_WIDTH = 176;
    static final int INVENTORY_HEIGHT = 166;
    static final int CELL = 18;
    static final int INSET = 7;
    static final int PREFERRED_COLUMNS = 8;
    static final int PREFERRED_ROWS = 8;
    private static final int INVENTORY_COLUMNS = 9;
    private static final int CRAFT_RESULT = 0;
    private static final int PLAYER_START = 5;
    private static final int PLAYER_END = PLAYER_START + 36;
    private static final int ARMOR_START = PLAYER_END + 1;
    static final int ACCESSORY_START = ARMOR_START + 4;

    enum Group { CURIOS, ACCESSORIES }

    record SlotKey(Group group, String name, int index, boolean cosmetic) {}

    record Layout(List<SlotKey> keys, Map<String, ICurioStacksHandler> curios,
                  Map<String, AccessoriesContainer> accessories) {
        static Layout forPlayer(Player player) {
            var curios = CuriosApi.getCuriosInventory(player).map(handler -> handler.getCurios()).orElse(Map.of());
            var accessories = AccessoriesCapability.getOptionally(player)
                .map(AccessoriesCapability::getContainers).orElse(Map.of());
            List<SlotKey> keys = new ArrayList<>();
            curios.keySet().stream().sorted().forEach(name -> {
                var handler = curios.get(name);
                if (handler.isVisible()) {
                    addKeys(keys, Group.CURIOS, name, handler.getStacks().getSlots(), false);
                    if (handler.hasCosmetic()) {
                        addKeys(keys, Group.CURIOS, name, handler.getCosmeticStacks().getSlots(), true);
                    }
                }
            });
            accessories.keySet().stream().sorted().forEach(name -> {
                var container = accessories.get(name);
                addKeys(keys, Group.ACCESSORIES, name, container.getSize(), false);
                addKeys(keys, Group.ACCESSORIES, name, container.getSize(), true);
            });
            return new Layout(List.copyOf(keys), Map.copyOf(curios), Map.copyOf(accessories));
        }

        private static void addKeys(List<SlotKey> keys, Group group, String name, int size, boolean cosmetic) {
            for (int index = 0; index < size; index++) {
                keys.add(new SlotKey(group, name, index, cosmetic));
            }
        }

        int signature() {
            int hash = 1;
            for (SlotKey key : keys) {
                hash = 31 * hash + key.group().ordinal();
                hash = 31 * hash + key.name().hashCode();
                hash = 31 * hash + key.index();
                hash = 31 * hash + (key.cosmetic() ? 1 : 0);
            }
            return hash;
        }
    }

    private final Player owner;
    private final Layout layout;
    private final TransientCraftingContainer craft = new TransientCraftingContainer(this, 2, 2);
    private final ResultContainer result = new ResultContainer();
    private final int[] cells;
    private final int accessoryCount;
    private final boolean layoutMatches;
    private final boolean hasCosmetics;
    private boolean showingCosmetics;
    private boolean accessoriesVisible = true;
    private int columns = PREFERRED_COLUMNS;
    private int rows = PREFERRED_ROWS;
    private int firstRow;

    static AccessoryMenu fromServer(int id, Inventory inventory, RegistryFriendlyByteBuf buffer) {
        int signature = buffer.readInt();
        int slotCount = buffer.readVarInt();
        if (slotCount < 0 || slotCount > 4096) {
            throw new IllegalArgumentException("Invalid accessory slot count: " + slotCount);
        }
        return new AccessoryMenu(id, inventory, Layout.forPlayer(inventory.player), signature, slotCount);
    }

    AccessoryMenu(int id, Inventory inventory, Layout layout) {
        this(id, inventory, layout, layout.signature(), layout.keys().size());
    }

    private AccessoryMenu(int id, Inventory inventory, Layout layout, int signature, int slotCount) {
        super(AccessoryMenuMod.MENU.get(), id);
        owner = inventory.player;
        this.layout = layout;
        layoutMatches = layout.keys().size() == slotCount && layout.signature() == signature;
        var equipmentCells = new HashMap<SlotKey, Integer>();
        for (SlotKey key : layout.keys()) {
            if (!key.cosmetic()) {
                equipmentCells.put(key, equipmentCells.size());
            }
        }
        accessoryCount = equipmentCells.size();
        hasCosmetics = layout.keys().stream().anyMatch(SlotKey::cosmetic);
        cells = new int[layout.keys().size()];

        addSlot(new CraftOutput(owner, craft, result));
        // The recipe book requires its result and four input slots at menu indices 0–4.
        for (int index = 0; index < 4; index++) {
            addSlot(new Slot(craft, index, 98 + index % 2 * CELL, 18 + index / 2 * CELL));
        }
        for (int index = 0; index < PLAYER_END - PLAYER_START; index++) {
            boolean hotbar = index < INVENTORY_COLUMNS;
            int y = hotbar ? 142 : 84 + (index / INVENTORY_COLUMNS - 1) * CELL;
            addSlot(new Slot(inventory, index, 8 + (index % INVENTORY_COLUMNS) * CELL, y));
        }
        addEquipment(inventory, owner.inventoryMenu.getSlot(InventoryMenu.SHIELD_SLOT), 77, 62);
        for (int index = 0; index < 4; index++) {
            addEquipment(inventory, owner.inventoryMenu.getSlot(InventoryMenu.ARMOR_SLOT_START + index),
                8, 8 + CELL * index);
        }
        if (!layoutMatches) {
            // Accept the server's initial slot synchronization without touching unmatched equipment.
            var placeholder = new SimpleContainer(slotCount);
            for (int index = 0; index < slotCount; index++) {
                addSlot(new Slot(placeholder, index, 0, 0) {
                    @Override
                    public boolean isActive() {
                        return false;
                    }
                });
            }
            return;
        }
        for (int i = 0; i < layout.keys().size(); i++) {
            SlotKey key = layout.keys().get(i);
            int cell = equipmentCells.getOrDefault(new SlotKey(key.group(), key.name(), key.index(), false), -1);
            cells[i] = cell;
            if (key.group() == Group.CURIOS) {
                var handler = layout.curios().get(key.name());
                var stacks = key.cosmetic() ? handler.getCosmeticStacks() : handler.getStacks();
                addSlot(new CurioSlot(owner, stacks, key.index(), key.name(), 0, 0, handler.getRenders(),
                    handler.getActiveStates(), handler.canToggleRendering(), false, key.cosmetic()) {
                    @Override
                    public boolean isActive() {
                        return super.isActive() && enabled(key, cell);
                    }

                    @Override
                    public com.mojang.datafixers.util.Pair<net.minecraft.resources.ResourceLocation,
                            net.minecraft.resources.ResourceLocation> getNoItemIcon() {
                        return CuriosApi.getSlot(key.name(), owner.level()).map(ISlotType::getIcon)
                            .map(icon -> com.mojang.datafixers.util.Pair.of(InventoryMenu.BLOCK_ATLAS, icon))
                            .orElseGet(super::getNoItemIcon);
                    }
                });
            } else {
                var container = layout.accessories().get(key.name());
                addSlot(new AccessoriesInternalSlot(container, key.cosmetic(), key.index(), 0, 0)
                    .isActive(slot -> enabled(key, cell)));
            }
        }
    }

    private void addEquipment(Inventory inventory, Slot original, int x, int y) {
        addSlot(new Slot(inventory, original.getContainerSlot(), x, y) {
            @Override
            public boolean mayPlace(ItemStack stack) {
                return original.mayPlace(stack);
            }

            @Override
            public boolean mayPickup(Player player) {
                return original.mayPickup(player);
            }

            @Override
            public int getMaxStackSize() {
                return original.getMaxStackSize();
            }

            @Override
            public void setByPlayer(ItemStack stack, ItemStack previous) {
                original.setByPlayer(stack, previous);
            }

            @Override
            public com.mojang.datafixers.util.Pair<net.minecraft.resources.ResourceLocation,
                    net.minecraft.resources.ResourceLocation> getNoItemIcon() {
                return original.getNoItemIcon();
            }
        });
    }

    @Override
    public void slotsChanged(Container container) {
        if (container == craft && !owner.level().isClientSide()) {
            CraftingMenuAccessor.callSlotChangedCraftingGrid(this, owner.level(), owner, craft, result, null);
        }
    }

    @Override
    public void removed(Player player) {
        super.removed(player);
        if (!player.level().isClientSide()) {
            clearContainer(player, craft);
        }
    }

    @Override
    public boolean canTakeItemForPickAll(ItemStack stack, Slot slot) {
        return slot.container != result && super.canTakeItemForPickAll(stack, slot);
    }

    private boolean enabled(SlotKey key, int cell) {
        return !owner.level().isClientSide() || (accessoriesVisible && showingCosmetics == key.cosmetic()
            && cell >= firstRow * columns && cell < (firstRow + rows) * columns);
    }

    boolean layoutMatches() {
        return layoutMatches;
    }

    boolean hasCosmetics() {
        return hasCosmetics;
    }

    boolean cosmetics() {
        return showingCosmetics;
    }

    void toggleCosmetics() {
        showingCosmetics = !showingCosmetics;
    }

    int accessoryCount() {
        return accessoryCount;
    }

    int accessoryCell(int slotIndex) {
        return cells[slotIndex - ACCESSORY_START];
    }

    int firstRow() {
        return firstRow;
    }

    int rowCount() {
        return Math.ceilDiv(accessoryCount, columns);
    }

    void setViewport(int columns, int rows) {
        this.columns = columns;
        this.rows = rows;
        scrollRows(0);
    }

    void scrollRows(int delta) {
        firstRow = Math.clamp(firstRow + delta, 0, Math.max(0, rowCount() - rows));
    }

    void setAccessoriesVisible(boolean visible) {
        accessoriesVisible = visible;
    }

    boolean renderEnabled(Slot slot) {
        if (slot instanceof CurioSlot curio) {
            return curio.getRenderStatus();
        }
        SlotKey key = layout.keys().get(slot.index - ACCESSORY_START);
        return layout.accessories().get(key.name()).shouldRender(key.index());
    }

    @Override
    public void fillCraftSlotsStackedContents(StackedContents contents) {
        craft.fillStackedContents(contents);
    }

    @Override
    public void clearCraftingContent() {
        result.clearContent();
        craft.clearContent();
    }

    @Override
    public boolean recipeMatches(RecipeHolder<CraftingRecipe> recipe) {
        return recipe.value().matches(craft.asCraftInput(), owner.level());
    }

    @Override
    public int getResultSlotIndex() {
        return CRAFT_RESULT;
    }

    @Override
    public int getGridWidth() {
        return 2;
    }

    @Override
    public int getGridHeight() {
        return 2;
    }

    @Override
    public int getSize() {
        return PLAYER_START;
    }

    @Override
    public RecipeBookType getRecipeBookType() {
        return RecipeBookType.CRAFTING;
    }

    @Override
    public boolean shouldMoveToInventory(int slot) {
        return slot != CRAFT_RESULT;
    }

    @Override
    public boolean stillValid(Player player) {
        if (player != owner || !player.isAlive() || !layoutMatches) {
            return false;
        }
        for (SlotKey key : layout.keys()) {
            if (key.group() == Group.CURIOS
                    ? key.index() >= layout.curios().get(key.name()).getSlots()
                    : key.index() >= layout.accessories().get(key.name()).getSize()) {
                return false;
            }
        }
        return true;
    }

    @Override
    public boolean clickMenuButton(Player player, int id) {
        if (player != owner || !stillValid(player) || id < ACCESSORY_START || id >= slots.size()) {
            return false;
        }
        SlotKey key = layout.keys().get(id - ACCESSORY_START);
        if (key.cosmetic()) {
            return false;
        }
        if (key.group() == Group.ACCESSORIES) {
            SyncCosmeticToggle.handlePacket(new SyncCosmeticToggle(null, key.name(), key.index()), player);
            return true;
        }
        CurioSlot slot = (CurioSlot) getSlot(id);
        if (player instanceof ServerPlayer serverPlayer && slot.canToggleRender()) {
            var renders = layout.curios().get(key.name()).getRenders();
            boolean visible = !renders.get(key.index());
            renders.set(key.index(), visible);
            PacketDistributor.sendToPlayersTrackingEntityAndSelf(
                serverPlayer, new SPacketSyncRender(player.getId(), key.name(), key.index(), visible));
            return true;
        }
        return false;
    }

    @Override
    public ItemStack quickMoveStack(Player player, int index) {
        if (index < 0 || index >= slots.size() || !stillValid(player)) {
            return ItemStack.EMPTY;
        }
        Slot slot = slots.get(index);
        if (!slot.hasItem() || !slot.mayPickup(player)) {
            return ItemStack.EMPTY;
        }
        ItemStack stack = slot.getItem();
        ItemStack before = stack.copy();
        int mainStart = PLAYER_START + INVENTORY_COLUMNS;
        if (index < PLAYER_START || index >= PLAYER_END) {
            if (!moveItemStackTo(stack, PLAYER_START, PLAYER_END, true)) {
                return ItemStack.EMPTY;
            }
        } else if (!equip(stack)) {
            boolean fromHotbar = index < mainStart;
            if (!moveItemStackTo(stack, fromHotbar ? mainStart : PLAYER_START,
                    fromHotbar ? PLAYER_END : mainStart, false)) {
                return ItemStack.EMPTY;
            }
        }
        if (index == CRAFT_RESULT) {
            ((CraftOutput) slot).takeQuickCraft(stack, before);
        }
        if (stack.isEmpty()) {
            slot.setByPlayer(ItemStack.EMPTY, before);
        } else {
            slot.setChanged();
        }
        slot.onTake(player, stack);
        if (index == CRAFT_RESULT && !stack.isEmpty()) {
            player.drop(stack, false);
        }
        return before;
    }

    private static final class CraftOutput extends ResultSlot {
        CraftOutput(Player owner, TransientCraftingContainer craft, ResultContainer result) {
            super(owner, craft, result, 0, 154, 28);
        }

        void takeQuickCraft(ItemStack remaining, ItemStack before) {
            onQuickCraft(remaining, before);
        }
    }

    private boolean equip(ItemStack stack) {
        for (int index = ARMOR_START; index < ACCESSORY_START; index++) {
            if (!slots.get(index).hasItem() && moveItemStackTo(stack, index, index + 1, false)) {
                return true;
            }
        }
        for (int i = 0; i < layout.keys().size(); i++) {
            int index = ACCESSORY_START + i;
            if (!layout.keys().get(i).cosmetic() && !slots.get(index).hasItem()
                    && moveItemStackTo(stack, index, index + 1, false)) {
                return true;
            }
        }
        return false;
    }
}
