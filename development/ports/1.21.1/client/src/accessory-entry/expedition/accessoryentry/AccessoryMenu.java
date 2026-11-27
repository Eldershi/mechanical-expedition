package expedition.accessoryentry;

import com.aetherteam.aether.mixin.mixins.common.accessor.CraftingMenuAccessor;
import io.wispforest.accessories.api.AccessoriesCapability;
import io.wispforest.accessories.api.AccessoriesContainer;
import io.wispforest.accessories.menu.AccessoriesInternalSlot;
import io.wispforest.accessories.networking.server.SyncCosmeticToggle;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.world.Container;
import net.minecraft.world.SimpleContainer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.inventory.AbstractContainerMenu;
import net.minecraft.world.inventory.InventoryMenu;
import net.minecraft.world.inventory.ResultContainer;
import net.minecraft.world.inventory.ResultSlot;
import net.minecraft.world.inventory.Slot;
import net.minecraft.world.inventory.TransientCraftingContainer;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.network.PacketDistributor;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.type.ISlotType;
import top.theillusivec4.curios.api.type.inventory.ICurioStacksHandler;
import top.theillusivec4.curios.common.inventory.CurioSlot;
import top.theillusivec4.curios.common.network.server.sync.SPacketSyncRender;

final class AccessoryMenu extends AbstractContainerMenu {
    static final int COLUMNS = 9;
    static final int PAGE_SIZE = COLUMNS * 2;
    static final int INVENTORY_Y = 133;
    private static final int PLAYER_SLOTS = 37;
    private static final int ARMOR_END = PLAYER_SLOTS + 5;
    private static final int CRAFT_RESULT = 0;
    private static final int PLAYER_START = 1;
    private static final int ACCESSORY_START = ARMOR_END + 5;

    enum Group {
        CURIOS(37), ACCESSORIES(87);

        final int y;

        Group(int y) {
            this.y = y;
        }
    }

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
    private final int[][] counts = new int[Group.values().length][2];
    private final int[] pages = new int[Group.values().length];
    private final boolean layoutMatches;
    private boolean showingCosmetics;

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
        addSlot(new CraftOutput(owner, craft, result));
        for (int index = 0; index < PLAYER_SLOTS - PLAYER_START; index++) {
            boolean hotbar = index < COLUMNS;
            int y = hotbar ? INVENTORY_Y + 58 : INVENTORY_Y + (index / COLUMNS - 1) * 18;
            addSlot(new Slot(inventory, index, 8 + (index % COLUMNS) * 18, y));
        }
        addEquipment(inventory, owner.inventoryMenu.getSlot(InventoryMenu.SHIELD_SLOT), 226, 94);
        for (int index = 0; index < 4; index++) {
            addEquipment(inventory, owner.inventoryMenu.getSlot(InventoryMenu.ARMOR_SLOT_START + index), 186, 24 + 18 * index);
        }
        for (int index = 0; index < 4; index++) {
            addSlot(new Slot(craft, index, 185 + (index % 2) * 18, 133 + (index / 2) * 18));
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
        for (SlotKey key : layout.keys()) {
            int i = counts[key.group().ordinal()][key.cosmetic() ? 1 : 0]++;
            int cell = i % PAGE_SIZE;
            int x = 8 + cell % COLUMNS * 18;
            int y = key.group().y + cell / COLUMNS * 18;
            int page = i / PAGE_SIZE;
            if (key.group() == Group.CURIOS) {
                var handler = layout.curios().get(key.name());
                var stacks = key.cosmetic() ? handler.getCosmeticStacks() : handler.getStacks();
                addSlot(new CurioSlot(owner, stacks, key.index(), key.name(), x, y, handler.getRenders(),
                    handler.getActiveStates(), handler.canToggleRendering(), false, key.cosmetic()) {
                    @Override
                    public boolean isActive() {
                        return super.isActive() && enabled(key, page);
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
                addSlot(new AccessoriesInternalSlot(container, key.cosmetic(), key.index(), x, y)
                    .isActive(slot -> enabled(key, page)));
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

    private boolean enabled(SlotKey key, int page) {
        return !owner.level().isClientSide()
            || showingCosmetics == key.cosmetic() && pages[key.group().ordinal()] == page;
    }

    boolean layoutMatches() {
        return layoutMatches;
    }

    boolean cosmetics() {
        return showingCosmetics;
    }

    void toggleCosmetics() {
        showingCosmetics = !showingCosmetics;
        Arrays.fill(pages, 0);
    }

    int page(Group group) {
        return pages[group.ordinal()];
    }

    int pages(Group group) {
        int count = counts[group.ordinal()][showingCosmetics ? 1 : 0];
        return Math.max(1, (count + PAGE_SIZE - 1) / PAGE_SIZE);
    }

    void changePage(Group group, int delta) {
        pages[group.ordinal()] = Math.clamp(page(group) + delta, 0, pages(group) - 1);
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
        if (index >= PLAYER_SLOTS || index == CRAFT_RESULT) {
            if (!moveItemStackTo(stack, PLAYER_START, PLAYER_SLOTS, true)) {
                return ItemStack.EMPTY;
            }
        } else if (!equip(stack) && !moveItemStackTo(stack, index <= COLUMNS ? COLUMNS + PLAYER_START : PLAYER_START,
                index <= COLUMNS ? PLAYER_SLOTS : COLUMNS + PLAYER_START, false)) {
            return ItemStack.EMPTY;
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
            super(owner, craft, result, 0, 247, 142);
        }

        void takeQuickCraft(ItemStack remaining, ItemStack before) {
            onQuickCraft(remaining, before);
        }
    }

    private boolean equip(ItemStack stack) {
        for (int index = PLAYER_SLOTS + 1; index < ARMOR_END; index++) {
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
