package expedition.rockgen;

import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BiomeTags;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.material.Fluids;
import net.neoforged.neoforge.items.ItemStackHandler;

import java.util.List;

final class RockGeneratorEntity extends BlockEntity {
    private static final int NORMAL_PERIOD = 20;
    private static final Direction[] SIDES = { Direction.NORTH, Direction.SOUTH, Direction.WEST, Direction.EAST };

    record Product(String coolant, String foundation, String item) {}

    private static final List<Product> PRODUCTS = List.of(
        new Product("minecraft:water", "minecraft:magma_block", "minecraft:stone"),
        new Product("minecraft:water", "create:andesite_alloy_block", "minecraft:andesite"),
        new Product("minecraft:water", "minecraft:dripstone_block", "create:limestone"),
        new Product("minecraft:blue_ice", "minecraft:soul_soil", "minecraft:basalt"),
        new Product("minecraft:packed_ice", "minecraft:magma_block", "minecraft:deepslate"),
        new Product("minecraft:basalt", "modernfoundry:magma_fluid", "modernfoundry:scorched_stone"),
        new Product("minecraft:water", null, "minecraft:cobblestone"),
        new Product("minecraft:blue_ice", null, "minecraft:blackstone"),
        new Product("minecraft:packed_ice", null, "minecraft:cobbled_deepslate"),
        new Product("create:chocolate", null, "create:scoria"),
        new Product("modernfoundry:molten_clay_fluid", null, "modernfoundry:seared_cobble")
    );

    private enum Redstone {
        IGNORED, LOW, HIGH;

        boolean permits(boolean powered) {
            return this == IGNORED || powered == (this == HIGH);
        }
    }

    private final ItemStackHandler output = new ItemStackHandler(1) {
        @Override
        public boolean isItemValid(int slot, ItemStack stack) {
            return false;
        }

        @Override
        protected void onContentsChanged(int slot) {
            setChanged();
        }
    };

    private Redstone redstone = Redstone.IGNORED;
    private Item product;
    private int progress;
    private int period = NORMAL_PERIOD;
    private boolean neighborsDirty = true;

    RockGeneratorEntity(BlockPos pos, BlockState state) {
        super(RockGeneratorMod.ENTITY.get(), pos, state);
    }

    ItemStackHandler output() {
        return output;
    }

    int comparatorStrength() {
        ItemStack stack = output.getStackInSlot(0);
        return stack.isEmpty() ? 0 : 1 + 14 * stack.getCount() / stack.getMaxStackSize();
    }

    void refreshNeighbors() {
        neighborsDirty = true;
    }

    void cycleRedstone() {
        Redstone[] modes = Redstone.values();
        redstone = modes[(redstone.ordinal() + 1) % modes.length];
        setChanged();
    }

    Component redstoneMessage() {
        return Component.translatable("block.expedition_rock_generator.redstone." +
            redstone.name().toLowerCase(java.util.Locale.ROOT));
    }

    void tick(ServerLevel level, BlockPos pos, BlockState state) {
        if (neighborsDirty || level.getGameTime() % NORMAL_PERIOD == 0) {
            updateProduct(level, pos);
        }

        boolean active = product != null && redstone.permits(level.hasNeighborSignal(pos));
        if (state.getValue(RockGeneratorBlock.ACTIVE) != active) {
            level.setBlock(pos, state.setValue(RockGeneratorBlock.ACTIVE, active), Block.UPDATE_CLIENTS);
        }
        if (!active) {
            return;
        }

        if (++progress >= period) {
            progress = 0;
            ItemStack stack = output.getStackInSlot(0);
            if (stack.isEmpty()) {
                output.setStackInSlot(0, new ItemStack(product));
            } else if (stack.getCount() < stack.getMaxStackSize()) {
                output.setStackInSlot(0, stack.copyWithCount(stack.getCount() + 1));
            }
        }
        level.blockEntityChanged(pos);
    }

    private void updateProduct(ServerLevel level, BlockPos pos) {
        if (!level.hasChunksAt(pos.offset(-1, -1, -1), pos.offset(1, 0, 1))) {
            product = null;
            neighborsDirty = true;
            return;
        }
        neighborsDirty = false;
        String[] coolants = new String[SIDES.length];
        boolean lava = false;
        for (int index = 0; index < SIDES.length; index++) {
            BlockState state = level.getBlockState(pos.relative(SIDES[index]));
            var fluid = state.getFluidState();
            lava |= fluid.is(Fluids.LAVA);
            if (fluid.isEmpty() || fluid.isSource()) {
                coolants[index] = BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();
            }
        }

        Item previous = product;
        product = lava ? matchProduct(coolants, BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos.below()).getBlock())
            .toString()) : null;
        if (product == null) {
            if (previous != null) {
                progress = 0;
                setChanged();
            }
            return;
        }
        ItemStack stack = output.getStackInSlot(0);
        if (!stack.isEmpty() && !stack.is(product)) {
            output.setStackInSlot(0, ItemStack.EMPTY);
        }
        period = level.getBiome(pos).is(BiomeTags.IS_NETHER) ? NORMAL_PERIOD / 2 : NORMAL_PERIOD;
    }

    private static Item matchProduct(String[] coolants, String foundation) {
        for (boolean requiresFoundation : new boolean[] {true, false}) {
            for (String coolant : coolants) {
                for (Product recipe : PRODUCTS) {
                    if (recipe.coolant().equals(coolant) && (requiresFoundation
                        ? foundation.equals(recipe.foundation()) : recipe.foundation() == null)) {
                        return BuiltInRegistries.ITEM.getOptional(ResourceLocation.parse(recipe.item())).orElse(null);
                    }
                }
            }
        }
        return null;
    }

    @Override
    protected void saveAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.saveAdditional(tag, registries);
        tag.put("Output", output.serializeNBT(registries));
        tag.putInt("Progress", progress);
        tag.putInt("Redstone", redstone.ordinal());
    }

    @Override
    protected void loadAdditional(CompoundTag tag, HolderLookup.Provider registries) {
        super.loadAdditional(tag, registries);
        output.deserializeNBT(registries, tag.getCompound("Output"));
        progress = Math.max(0, Math.min(NORMAL_PERIOD - 1, tag.getInt("Progress")));
        int mode = tag.getInt("Redstone");
        redstone = mode >= 0 && mode < Redstone.values().length ? Redstone.values()[mode] : Redstone.IGNORED;
        refreshNeighbors();
    }
}
