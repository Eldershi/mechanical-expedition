package expedition.radaracquisition;

import cn.dancingsnow.neoecoae.blocks.entity.ECOIntegratedWorkingStationBlockEntity;
import cn.dancingsnow.neoecoae.recipe.IntegratedWorkingStationRecipe;
import com.negodya1.vintageimprovements.content.kinetics.curving_press.CurvingRecipe;
import com.negodya1.vintageimprovements.content.kinetics.laser.LaserCuttingRecipe;
import com.simibubi.create.content.fluids.spout.FillingBySpout;
import com.simibubi.create.content.kinetics.base.DirectionalKineticBlock;
import com.simibubi.create.content.kinetics.base.HorizontalKineticBlock;
import com.simibubi.create.content.kinetics.press.MechanicalPressBlockEntity;
import com.simibubi.create.content.processing.basin.BasinBlockEntity;
import com.simibubi.create.content.processing.basin.BasinRecipe;
import com.simibubi.create.content.processing.burner.BlazeBurnerBlock;
import com.simibubi.create.content.processing.recipe.ProcessingRecipe;
import com.simibubi.create.content.processing.sequenced.SequencedAssemblyRecipe;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Optional;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.block.Block;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.IFluidHandler;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.items.ItemHandlerHelper;

@Mod("expedition_radar_acquisition_probe")
public final class RadarAcquisitionAcceptance {
    private static final BlockPos STATION = new BlockPos(11, -40, 8);
    private static final BlockPos PRESS = new BlockPos(5, -40, 12);
    private static final String PATH = "expedition:radar/acquisition/";
    private static final List<String> PRESS_OUTPUTS = List.of(
        "smart_casing", "engineering_mechanism_part", "smart_mechanism_augment"
    );
    private static final List<String> STATION_OUTPUTS = List.of(
        "space_mechanism_part", "aeronautic_mechanism_basement", "aeronautic_mechanism",
        "power_supply", "transformer", "tracking_array", "modem", "radar", "radar_antenna"
    );

    private final List<ItemStack> produced = new ArrayList<>();
    private ServerLevel level;
    private ECOIntegratedWorkingStationBlockEntity station;
    private BasinBlockEntity pressBasin;
    private IntegratedWorkingStationRecipe running;
    private boolean observedWorking;
    private int ticks;
    private int index;
    private int pressIndex;

    public RadarAcquisitionAcceptance() {
        NeoForge.EVENT_BUS.addListener(this::register);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionradaracquisition")
            .requires(source -> source.hasPermission(4)).executes(context -> {
                level = context.getSource().getLevel();
                level.setChunkForced(0, 0, true);
                return 1;
            }));
    }

    private void tick(ServerTickEvent.Post event) {
        if (level == null) return;
        try {
            if (pressBasin == null && level.hasChunkAt(PRESS)) prepare();
            if (station != null && station.getMainNode().isActive()) {
                if (running == null && index < STATION_OUTPUTS.size()) startNext();
                else if (running != null) awaitOutput();
            }
            if (pressBasin != null && pressIndex < PRESS_OUTPUTS.size()) checkPressOutput();
            if (index == STATION_OUTPUTS.size()) {
                System.out.println("EXPEDITION_RADAR_ACQUISITION_PASS");
                stop();
                return;
            }
            if (++ticks > 500) throw new IllegalStateException("Acquisition timeout after " + index
                + " output(s), active=" + (station != null && station.getMainNode().isActive())
                + " progress=" + (station == null ? 0 : station.getProcessingTime())
                + " press outputs=" + pressIndex + " press=" + pressStatus());
        } catch (Exception error) {
            error.printStackTrace();
            System.out.println("EXPEDITION_RADAR_ACQUISITION_FAILED " + error);
            stop();
        }
    }

    private void prepare() {
        for (var recipe : List.of("stainless_steel_plate", "aluminum_alloy_plate", "manyullyn_gear",
                "glass_rod", "glass_wire", "optical_fiber", "ferrit_core", "molten_etrium", "molten_fluix",
                "fluix_wire", "deposition_catalytic_alloy", "carbon_deposition_catalytic_plate", "graphene")) {
            require(recipe(recipe) != null, "missing material recipe " + recipe);
        }
        require(level.getServer().getRecipeManager().byKey(ResourceLocation.parse(
            "expedition:factory/silicone/silicon_rubber_plate")).isPresent(), "missing silicone rubber plate recipe");
        for (var color : List.of("light_gray", "white")) checkConcreteFilling(color);
        var empty = (SequencedAssemblyRecipe) recipe("empty_cell");
        require(empty.getSequence().size() == 4 && empty.getLoops() == 1, "unexpected empty disk sequence");
        var laser = (LaserCuttingRecipe) empty.getSequence().get(2).getRecipe();
        require(laser.getEnergy() == 4000 && laser.getMaxChargeRate() == 4000, "laser power changed");
        require(((CurvingRecipe) empty.getSequence().get(3).getRecipe()).getMode() == 3, "W-head mode changed");
        require(empty.getSequence().get(1).getRecipe().getIngredients()
            .stream().anyMatch(i -> i.test(stack("cmi:manyullyn_gear"))), "missing Manyullyn gear step");
        completeSequence("empty_cell", "cmi:empty_cell");
        preparePress();
    }

    private void prepareStation() {
        level.setBlock(STATION, block("neoecoae:integrated_working_station").defaultBlockState(), Block.UPDATE_ALL);
        level.setBlock(STATION.east(), block("ae2:creative_energy_cell").defaultBlockState(), Block.UPDATE_ALL);
        station = (ECOIntegratedWorkingStationBlockEntity) level.getBlockEntity(STATION);
        require(station != null, "workstation did not create block entity");
    }

    private void preparePress() {
        var basinPos = PRESS.below(2);
        var burnerPos = PRESS.below(3);
        if (level.getBlockEntity(basinPos) instanceof BasinBlockEntity previous) previous.clearContent();
        for (var pos : List.of(PRESS.west(), PRESS, basinPos, burnerPos)) level.removeBlock(pos, false);
        level.setBlock(burnerPos, block("create:blaze_burner").defaultBlockState().setValue(
            BlazeBurnerBlock.HEAT_LEVEL, BlazeBurnerBlock.HeatLevel.SMOULDERING), Block.UPDATE_ALL);
        level.setBlock(basinPos, block("create:basin").defaultBlockState(), Block.UPDATE_ALL);
        pressBasin = (BasinBlockEntity) level.getBlockEntity(basinPos);
        var recipe = loadPress();
        require(recipe.getIngredients().stream().anyMatch(i -> i.test(stack("cmi:silicon_rubber")))
            && recipe.getFluidIngredients().size() == 1 && recipe.getFluidIngredients().getFirst().amount() == 100,
            "casing recipe must distinguish the rubber item from the liquid binder");
        require(!BasinRecipe.match(pressBasin, recipe), "unheated basin matched casing recipe");
        var fuel = BlazeBurnerBlock.tryInsert(level.getBlockState(burnerPos), level, burnerPos,
            stack("minecraft:coal"), false, false, false);
        require(fuel.getResult().consumesAction(), "burner rejected coal");
        level.setBlock(PRESS, block("create:mechanical_press").defaultBlockState().setValue(
            HorizontalKineticBlock.HORIZONTAL_FACING, Direction.EAST), Block.UPDATE_ALL);
        level.setBlock(PRESS.west(), block("create:creative_motor").defaultBlockState().setValue(
            DirectionalKineticBlock.FACING, Direction.EAST), Block.UPDATE_ALL);
        pressBasin.notifyChangeOfContents();
    }

    private BasinRecipe loadPress() {
        var recipe = (BasinRecipe) recipe(PRESS_OUTPUTS.get(pressIndex));
        var input = pressBasin.getInputInventory();
        for (var ingredient : recipe.getIngredients()) {
            var stack = ingredient.getItems()[0];
            require(ItemHandlerHelper.insertItemStacked(input, stack.copyWithCount(1), false).isEmpty(),
                "basin rejected press material " + stack);
        }
        for (var ingredient : recipe.getFluidIngredients()) {
            var binder = ingredient.ingredient().getStacks()[0].copy();
            binder.setAmount(ingredient.amount());
            var fluids = level.getCapability(Capabilities.FluidHandler.BLOCK, pressBasin.getBlockPos(), Direction.UP);
            require(fluids != null && fluids.fill(binder, IFluidHandler.FluidAction.EXECUTE) == binder.getAmount(),
                "basin rejected press fluid " + binder);
        }
        return recipe;
    }

    private void checkPressOutput() {
        var outputs = pressBasin.getOutputInventory();
        var expected = stack("cmi:" + PRESS_OUTPUTS.get(pressIndex)).copyWithCount(pressIndex == 0 ? 2 : 4);
        for (int slot = 0; slot < outputs.getSlots(); slot++) {
            if (!ItemStack.matches(outputs.extractItem(slot, 64, true), expected)) continue;
            var extracted = outputs.extractItem(slot, 64, false);
            require(ItemStack.matches(extracted, expected), "pressed product did not extract");
            produced.add(extracted);
            System.out.println("EXPEDITION_RADAR_PRESS_RESULT product=" + extracted);
            ticks = 0;
            if (++pressIndex < PRESS_OUTPUTS.size()) loadPress();
            else {
                produced.add(completeSequence("smart_mechanism", "cmi:smart_mechanism"));
                produced.add(completeSequence("smart_mechanism", "cmi:smart_mechanism"));
                prepareStation();
            }
            return;
        }
    }

    private String pressStatus() {
        var operator = level.getBlockEntity(PRESS);
        if (!(operator instanceof MechanicalPressBlockEntity press) || pressBasin == null) return "not built";
        if (pressIndex == PRESS_OUTPUTS.size()) return "complete";
        return "speed=" + press.getSpeed() + " heat=" + BlazeBurnerBlock.getHeatLevelOf(
            level.getBlockState(PRESS.below(3))) + " inputMatches="
            + BasinRecipe.match(pressBasin, recipe(PRESS_OUTPUTS.get(pressIndex)));
    }

    private void checkConcreteFilling(String color) {
        var product = color + "_reinforced_concrete";
        var cement = ResourceLocation.parse("createdieselgenerators:" + color + "_cement");
        var mixerRecipe = ResourceLocation.parse("createdieselgenerators:mixing/" + color + "_concrete");
        require(level.getServer().getRecipeManager().byKey(mixerRecipe).isPresent(), "no mixer recipe for " + cement);
        require(recipe(product) != null, "missing reinforced concrete recipe");
        var fluid = new FluidStack(BuiltInRegistries.FLUID.get(cement), 1000);
        var frame = stack("immersiveengineering:steel_scaffolding_standard");
        int amount = FillingBySpout.getRequiredAmountForItem(level, frame, fluid);
        require(amount == 1000, "wrong cement requirement " + amount);
        var result = FillingBySpout.fillItem(level, amount, frame, fluid);
        require(ItemStack.matches(result, stack("cmi:" + product)), "wrong concrete " + result);
        System.out.println("EXPEDITION_RADAR_SPOUT_RESULT product=" + result);
    }

    private void startNext() {
        final var name = STATION_OUTPUTS.get(index);
        running = (IntegratedWorkingStationRecipe) recipe(name);
        var items = items();
        for (int i = 0; i < running.inputItems().size(); i++) {
            var ingredient = running.inputItems().get(i);
            var matched = Arrays.stream(ingredient.ingredient().getItems()).findFirst()
                .orElseThrow(() -> new IllegalStateException("empty ingredient in " + name));
            var input = produced.stream().filter(candidate -> candidate.getCount() >= ingredient.count()
                && ingredient.ingredient().test(candidate)).findFirst().orElse(matched.copyWithCount(ingredient.count()));
            require(items.insertItem(i, input.split(ingredient.count()), false).isEmpty(),
                "workstation rejected input " + matched + " in " + name);
        }
        if (!running.inputFluid().ingredient().isEmpty()) {
            var fluid = running.inputFluid().ingredient().getStacks()[0].copy();
            fluid.setAmount(running.inputFluid().amount());
            require(station.getFluidCombined().fill(fluid, IFluidHandler.FluidAction.EXECUTE) == fluid.getAmount(),
                "workstation rejected fluid in " + name);
        }
        ticks = 0;
        observedWorking = false;
    }

    private void awaitOutput() {
        observedWorking |= station.isWorking();
        var items = items();
        for (int slot = 0; slot < items.getSlots(); slot++) {
            var result = items.extractItem(slot, 64, true);
            if (!ItemStack.matches(result, running.itemOutput())) continue;
            require(observedWorking, "workstation never reported processing");
            var extracted = items.extractItem(slot, 64, false);
            require(ItemStack.matches(extracted, result), "output did not extract");
            produced.add(extracted);
            System.out.println("EXPEDITION_RADAR_WORKSTATION_RESULT product=" + result + " energy=" + running.energy());
            running = null;
            ticks = 0;
            index++;
            return;
        }
    }

    @SuppressWarnings({"rawtypes", "unchecked"})
    private ItemStack completeSequence(String name, String output) {
        var recipe = (SequencedAssemblyRecipe) recipe(name);
        var stack = Arrays.stream(recipe.getIngredient().getItems()).findFirst().orElseThrow().copy();
        var id = ResourceLocation.parse(PATH + name);
        for (var step : recipe.getSequence()) {
            var expected = step.getRecipe();
            require(expected.getIngredients().stream().allMatch(i -> i.getItems().length > 0),
                "unavailable machine ingredient in " + name);
            require(expected.getFluidIngredients().stream().allMatch(i -> i.ingredient().getStacks().length > 0),
                "unavailable machine fluid in " + name);
            Optional<?> stepMatch = SequencedAssemblyRecipe.getRecipe(
                level, stack, (RecipeType) expected.getType(), ProcessingRecipe.class
            );
            var hit = (RecipeHolder<?>) stepMatch
                .orElseThrow(() -> new IllegalStateException("Create did not select a step in " + id));
            var results = ((ProcessingRecipe<?, ?>) hit.value()).rollResults(level.getRandom());
            require(results.size() == 1 && !results.getFirst().isEmpty(), "step did not yield a result");
            stack = results.getFirst();
        }
        require(ItemStack.matches(stack, stack(output)), "wrong sequenced output " + stack + " from " + id);
        System.out.println("EXPEDITION_RADAR_CREATE_SEQUENCE output=" + stack + " steps=" + recipe.getSequence().size());
        return stack;
    }

    private Recipe<?> recipe(String name) {
        return level.getServer().getRecipeManager().byKey(ResourceLocation.parse(PATH + name))
            .orElseThrow(() -> new IllegalStateException("recipe missing " + name)).value();
    }

    private IItemHandler items() {
        return java.util.Objects.requireNonNull(level.getCapability(Capabilities.ItemHandler.BLOCK, STATION, Direction.UP));
    }

    private void stop() {
        level.setChunkForced(0, 0, false);
        level = null;
    }

    private static ItemStack stack(String id) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));
    }

    private static Block block(String id) {
        return BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
