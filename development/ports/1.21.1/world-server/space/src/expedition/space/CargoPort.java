package expedition.space;

import expedition.space.FreightData.Role;
import expedition.space.FreightData.Station;
import net.minecraft.core.Direction;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.neoforged.neoforge.items.IItemHandler;

final class CargoPort implements IItemHandler {
    private final ServerLevel level;
    private final Station station;
    private final boolean output;
    private final boolean launch;

    CargoPort(ServerLevel level, Station station, Direction face) {
        this.level = level;
        this.station = station;
        this.output = face == Direction.DOWN || station.key.role() == Role.BEACON;
        this.launch = station.key.role() == Role.LAUNCH;
    }

    @Override
    public int getSlots() { return FreightData.BATCH + (launch ? output ? 1 : 2 : 0); }

    private int index(int slot) {
        if (slot >= FreightData.BATCH) return output ? FreightData.FUEL : FreightData.CARRIER + slot - FreightData.BATCH;
        return output ? FreightData.OUTPUT + slot : slot;
    }

    @Override
    public ItemStack getStackInSlot(int slot) {
        return SpaceLogistics.operational(level.getServer(), station) ? station.getItem(index(slot)).copy() : ItemStack.EMPTY;
    }

    @Override
    public ItemStack insertItem(int slot, ItemStack stack, boolean simulate) {
        if (stack.isEmpty() || !isItemValid(slot, stack) || !SpaceLogistics.operational(level.getServer(), station)) return stack;
        int index = index(slot);
        ItemStack current = station.getItem(index);
        if (!current.isEmpty() && !ItemStack.isSameItemSameComponents(current, stack)) return stack;
        int count = Math.min(stack.getCount(), Math.min(getSlotLimit(slot), stack.getMaxStackSize()) - current.getCount());
        if (count <= 0) return stack;
        if (!simulate) station.setItem(index, stack.copyWithCount(current.getCount() + count));
        return stack.copyWithCount(stack.getCount() - count);
    }

    @Override
    public ItemStack extractItem(int slot, int amount, boolean simulate) {
        if (!output || amount <= 0 || !SpaceLogistics.operational(level.getServer(), station)) return ItemStack.EMPTY;
        ItemStack current = station.getItem(index(slot));
        if (current.isEmpty() || slot >= FreightData.BATCH && !current.is(Items.BUCKET)) return ItemStack.EMPTY;
        int count = Math.min(amount, current.getCount());
        ItemStack result = current.copyWithCount(count);
        if (!simulate) station.setItem(index(slot), current.copyWithCount(current.getCount() - count));
        return result;
    }

    @Override
    public int getSlotLimit(int slot) { return slot >= FreightData.BATCH ? 1 : 64; }

    @Override
    public boolean isItemValid(int slot, ItemStack stack) {
        return !output && (slot < FreightData.BATCH || (launch && SpaceLogistics.correctSupply(index(slot), stack)));
    }
}
