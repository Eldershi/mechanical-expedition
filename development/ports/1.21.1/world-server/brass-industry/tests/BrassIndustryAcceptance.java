package expedition.industry;

import com.google.gson.JsonParser;
import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.lowdragmc.mbd2.common.trait.fluid.FluidTankCapabilityTrait;
import com.lowdragmc.mbd2.common.trait.forgeenergy.ForgeEnergyCapabilityTrait;
import com.lowdragmc.mbd2.common.trait.item.ItemSlotCapabilityTrait;
import com.simibubi.create.content.processing.recipe.ProcessingRecipe;
import com.simibubi.create.content.processing.sequenced.SequencedAssemblyRecipe;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.level.block.Block;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.IFluidHandler.FluidAction;

public final class BrassIndustryAcceptance {
    private static final String NS = "expedition_industry:";
    private record Sample(String machine, String item, int count, String fluid, int amount, String result, int output) {}
    private record Fixture(Sample sample, BlockPos controller) {}
    private static final List<Sample> SAMPLES = List.of(
        new Sample("alloy_furnace", "minecraft:raw_copper", 4, "", 0, "modernfoundry:molten_copper", 360),
        new Sample("blasting_compressor", "minecraft:coal_block", 16, "", 0, "minecraft:diamond", 1),
        new Sample("condenser", NS + "coolant", 1, "", 0, NS + "liquid_air", 1000),
        new Sample("electro_hydro_resonant_tower", NS + "graphite_dust", 4, NS + "electro_hydro_fluid", 250, "cmi:graphene", 2),
        new Sample("electrolytic_cell", "", 0, "minecraft:water", 1000, "mekanism:hydrogen", 666),
        new Sample("electron_tube_computer", "", 0, "", 0, NS + "data_kib", 1),
        new Sample("huge_crusher", "minecraft:cobblestone", 16, "minecraft:water", 1000, "minecraft:gravel", 16),
        new Sample("hydropress", "create:brass_block", 1, "", 0, "create:brass_sheet", 9),
        new Sample("infinity_fetching_pool", "", 0, "minecraft:water", 250, "minecraft:water", 1000),
        new Sample("large_difference_engine", "", 0, "", 0, NS + "data_mib", 1),
        new Sample("shaft_furnace", NS + "semi_finished_steel", 4, "", 0, "modernfoundry:molten_steel", 360),
        new Sample("trading_station", "minecraft:copper_block", 1, "", 0, NS + "trade_credit", 2)
    );
    private final List<Fixture> placed = new ArrayList<>();
    private final List<Fixture> running = new ArrayList<>();
    private long start = -1;

    public BrassIndustryAcceptance() {
        NeoForge.EVENT_BUS.addListener(this::commands);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void commands(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionbrassproof").requires(source -> source.hasPermission(4))
            .executes(context -> {
                begin(context.getSource().getServer().overworld());
                return 1;
            }));
    }

    private void begin(ServerLevel level) {
        placed.clear();
        running.clear();
        checkDifferential(level);
        try {
            var layouts = JsonParser.parseString(Files.readString(Path.of("brass-fixtures.json"))).getAsJsonObject();
            for (int index = 0; index < SAMPLES.size(); index++) {
                Sample sample = SAMPLES.get(index);
                try {
                    BlockPos origin = new BlockPos(320 + 20 * (index % 4), 140, 320 + 24 * (index / 4));
                    BlockPos controller = null;
                    for (var entry : layouts.getAsJsonArray(sample.machine)) {
                        var cell = entry.getAsJsonArray();
                        BlockPos pos = origin.offset(cell.get(0).getAsInt(), cell.get(1).getAsInt(), cell.get(2).getAsInt());
                        level.setChunkForced(pos.getX() >> 4, pos.getZ() >> 4, true);
                        String state = cell.get(3).getAsString();
                        var parsed = BlockStateParser.parseForBlock(level.registryAccess().lookupOrThrow(Registries.BLOCK), state, false);
                        level.setBlock(pos, parsed.blockState(), Block.UPDATE_CLIENTS);
                        if (state.equals(NS + sample.machine)) controller = pos;
                    }
                    if (controller == null) throw new IllegalStateException("missing controller");
                    var machine = machine(level, controller);
                    machine.setFrontFacing(Direction.NORTH);
                    machine.notifyPatternDirty();
                    placed.add(new Fixture(sample, controller));
                } catch (Exception error) {
                    System.out.println("EXPEDITION_BRASS_PLACE_FAIL " + sample.machine + " " + error);
                }
            }
        } catch (Exception error) {
            throw new IllegalStateException("invalid fixture input", error);
        }
        start = level.getGameTime();
    }

    private void tick(ServerTickEvent.Post event) {
        if (start < 0) return;
        ServerLevel level = event.getServer().overworld();
        long elapsed = level.getGameTime() - start;
        if (elapsed == 45) {
            for (Fixture fixture : placed) {
                var machine = machine(level, fixture.controller);
                if (!machine.isFormedValid()) {
                    var state = machine.getMultiblockState();
                    BlockPos pos = state.getPos();
                    System.out.println("EXPEDITION_BRASS_FORM_FAIL " + fixture.sample.machine + " at " + pos
                        + " actual " + (pos == null ? "no position" : level.getBlockState(pos)));
                    continue;
                }
                try {
                    checkCraft(level, fixture.sample.machine);
                    feed(machine, fixture.sample);
                    running.add(fixture);
                    System.out.println("EXPEDITION_BRASS_FORM_PASS " + fixture.sample.machine);
                } catch (Exception error) {
                    System.out.println("EXPEDITION_BRASS_SETUP_FAIL " + fixture.sample.machine + " " + error);
                }
            }
        } else if (elapsed >= 385) {
            int successes = 0;
            for (Fixture fixture : running) {
                if (produced(machine(level, fixture.controller), fixture.sample)) {
                    successes++;
                    System.out.println("EXPEDITION_BRASS_OUTPUT_PASS " + fixture.sample.machine);
                } else {
                    System.out.println("EXPEDITION_BRASS_OUTPUT_FAIL " + fixture.sample.machine);
                }
            }
            System.out.println("EXPEDITION_BRASS_COMPLETE " + successes + "/" + SAMPLES.size());
            start = -1;
        }
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private static void checkDifferential(ServerLevel level) {
        var recipe = level.getRecipeManager().byKey(id(NS + "differential")).orElseThrow().value();
        if (!(recipe instanceof SequencedAssemblyRecipe sequence)
                || sequence.getLoops() != 1 || sequence.getSequence().size() != 3
                || !sequence.getIngredient().test(stack("create:brass_sheet", 1))
                || sequence.getResultItem(level.registryAccess()).getCount() != 2
                || !sequence.getResultItem(level.registryAccess()).is(stack(NS + "differential", 1).getItem())) {
            throw new IllegalStateException("differential recipe");
        }
        ItemStack substrate = stack("create:brass_sheet", 1);
        for (int i = 0; i < 3; i++) {
            var expected = sequence.getSequence().get(i).getRecipe();
            var ingredient = expected.getIngredients().get(1);
            if (!ingredient.test(stack(i == 2 ? "create:precision_mechanism" : "create:large_cogwheel", 1))) {
                throw new IllegalStateException("differential sequence step " + i);
            }
            var holder = (RecipeHolder<?>) SequencedAssemblyRecipe.getRecipe(
                level, substrate, (RecipeType) expected.getType(), ProcessingRecipe.class).orElseThrow();
            substrate = ((ProcessingRecipe<?, ?>) holder.value()).rollResults(level.getRandom()).getFirst();
        }
        if (!ItemStack.matches(substrate, stack(NS + "differential", 2))) {
            throw new IllegalStateException("wrong deployed differential result " + substrate);
        }
        System.out.println("EXPEDITION_DIFFERENTIAL_RECIPE_PASS");
    }

    private static void checkCraft(ServerLevel level, String name) {
        var recipe = (ShapedRecipe) level.getRecipeManager().byKey(id(NS + "controller/" + name)).orElseThrow().value();
        List<ItemStack> grid = new ArrayList<>(9);
        for (var ingredient : recipe.getIngredients()) {
            if (ingredient.getItems().length == 0) throw new IllegalStateException("empty ingredient");
            grid.add(ingredient.getItems()[0].copy());
        }
        var output = recipe.assemble(CraftingInput.of(3, 3, grid), level.registryAccess());
        if (!recipe.matches(CraftingInput.of(3, 3, grid), level) || !output.is(stack(NS + name, 1).getItem())
                || output.getCount() != (name.equals("trading_station") ? 4 : 1)) {
            throw new IllegalStateException("controller craft");
        }
    }

    private static void feed(MBDMultiblockMachine machine, Sample sample) {
        var energy = machine.getTraitByName(ForgeEnergyCapabilityTrait.class, "forge_energy_storage").getStorage();
        for (int i = 0; i < 28; i++) energy.receiveEnergy(8_000, false);
        var input = machine.getTraitByName(ItemSlotCapabilityTrait.class, "item_input").storage;
        if (sample.count > 0) input.setStackInSlot(0, stack(sample.item, sample.count));
        if (sample.machine.equals("shaft_furnace")) input.setStackInSlot(1, stack(NS + "aluminum_slag", 1));
        if (sample.machine.equals("blasting_compressor")) input.setStackInSlot(1, stack("minecraft:tnt", 1));
        if (sample.amount > 0) {
            var tank = machine.getTraitByName(FluidTankCapabilityTrait.class, "fluid_input");
            tank.storages[0].fill(new FluidStack(BuiltInRegistries.FLUID.get(id(sample.fluid)), sample.amount), FluidAction.EXECUTE);
        }
    }

    private static boolean produced(MBDMultiblockMachine machine, Sample sample) {
        var result = id(sample.result);
        var items = machine.getTraitByName(ItemSlotCapabilityTrait.class, "item_output").storage;
        int amount = 0;
        for (int i = 0; i < items.getSlots(); i++) {
            var actual = items.getStackInSlot(i);
            if (BuiltInRegistries.ITEM.getKey(actual.getItem()).equals(result)) amount += actual.getCount();
        }
        var tank = machine.getTraitByName(FluidTankCapabilityTrait.class, "fluid_output");
        if (tank != null) {
            for (var storage : tank.storages) {
                var actual = storage.getFluidInTank(0);
                if (BuiltInRegistries.FLUID.getKey(actual.getFluid()).equals(result)) amount += actual.getAmount();
            }
        }
        return amount >= sample.output;
    }

    private static MBDMultiblockMachine machine(ServerLevel level, BlockPos pos) {
        return (MBDMultiblockMachine) IMultiController.ofController(level, pos).orElseThrow();
    }

    private static ResourceLocation id(String id) {
        return ResourceLocation.parse(id);
    }

    private static ItemStack stack(String id, int count) {
        var item = BuiltInRegistries.ITEM.get(id(id));
        if (item == Items.AIR) throw new IllegalStateException("unknown item " + id);
        return new ItemStack(item, count);
    }
}
