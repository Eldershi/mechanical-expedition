package expedition.engineering;

import java.util.Objects;

import blusunrize.immersiveengineering.common.blocks.multiblocks.logic.arcfurnace.ArcFurnaceLogic;
import blusunrize.immersiveengineering.common.items.GraphiteElectrodeItem;
import net.minecraft.world.item.ItemStack;
import net.neoforged.neoforge.items.IItemHandler;

public record ElectrodeHandler(IItemHandler inventory) implements IItemHandler {
    @Override
    public int getSlots() {
        return ArcFurnaceLogic.ELECTRODE_COUNT;
    }

    @Override
    public ItemStack getStackInSlot(int slot) {
        return inventory.getStackInSlot(inventorySlot(slot));
    }

    @Override
    public ItemStack insertItem(int slot, ItemStack stack, boolean simulate) {
        return isItemValid(slot, stack) ? inventory.insertItem(inventorySlot(slot), stack, simulate) : stack;
    }

    @Override
    public ItemStack extractItem(int slot, int count, boolean simulate) {
        return inventory.extractItem(inventorySlot(slot), count, simulate);
    }

    @Override
    public int getSlotLimit(int slot) {
        return inventory.getSlotLimit(inventorySlot(slot));
    }

    @Override
    public boolean isItemValid(int slot, ItemStack stack) {
        return stack.getItem() instanceof GraphiteElectrodeItem
            && inventory.isItemValid(inventorySlot(slot), stack);
    }

    private int inventorySlot(int slot) {
        return ArcFurnaceLogic.FIRST_ELECTRODE_SLOT + Objects.checkIndex(slot, getSlots());
    }
}
