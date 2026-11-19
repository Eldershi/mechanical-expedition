package expedition.qa.airtight;

import java.util.Arrays;
import java.util.List;
import java.util.stream.Stream;

import cn.dancingsnow.neoecoae.blocks.entity.ECOIntegratedWorkingStationBlockEntity;
import cn.dancingsnow.neoecoae.recipe.IntegratedWorkingStationRecipe;
import com.simibubi.create.content.processing.basin.BasinBlockEntity;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.core.registries.Registries;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.CraftingInput;
import net.minecraft.world.item.crafting.CraftingRecipe;
import net.minecraft.world.item.crafting.ShapedRecipe;
import net.minecraft.world.item.crafting.SingleRecipeInput;
import net.minecraft.world.item.crafting.StonecutterRecipe;
import net.minecraft.world.level.block.Block;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.fluids.capability.IFluidHandler.FluidAction;
import net.neoforged.neoforge.items.IItemHandler;
import net.neoforged.neoforge.items.ItemHandlerHelper;
import net.ty.createcraftedbeginning.api.gas.GasAction;
import net.ty.createcraftedbeginning.api.gas.GasStack;
import net.ty.createcraftedbeginning.content.airtights.gasinjectionchamber.GasInjectionChamberBlockEntity;
import net.ty.createcraftedbeginning.registry.gas.CCBGases;

@Mod("expedition_airtight_acceptance")
public final class AirtightEquipmentAcceptance {
    private static final BlockPos STATION = new BlockPos(8, 252, 9);
    private static final BlockPos BASIN = STATION.west(3);
    private static final String AIR = "cmi:air_tight_mechanism";
    private static final String CANISTER = "createcraftedbeginning:gas_canister";
    private static final String SEALING = "expedition:factory/pneumatic_sealing/";
    private static final String EQUIPMENT = "expedition:factory/airtight_equipment/";
    private static final List<String> MACHINES = List.of(
        "osmium_compressor", "purification_chamber", "chemical_oxidizer", "chemical_injection_chamber",
        "chemical_infuser", "isotopic_centrifuge", "chemical_dissolution_chamber", "chemical_washer",
        "chemical_crystallizer", "solar_neutron_activator", "pressurized_reaction_chamber"
    );
    private static final List<String> STATION_RECIPES = Stream.concat(
        Stream.of(SEALING + "air_tight_mechanism_basement", SEALING + "incomplete_air_tight_mechanism"),
        MACHINES.stream().map(EQUIPMENT::concat)).toList();

    private ServerLevel level;
    private ECOIntegratedWorkingStationBlockEntity station;
    private IntegratedWorkingStationRecipe current;
    private ItemStack basement = ItemStack.EMPTY;
    private ItemStack sealed = ItemStack.EMPTY;
    private BasinBlockEntity basin;
    private GasInjectionChamberBlockEntity chamber;
    private int index;
    private int ticks;

    public AirtightEquipmentAcceptance() {
        NeoForge.EVENT_BUS.addListener(this::register);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionairtightproof").requires(source -> source.hasPermission(4))
            .executes(context -> {
                level = context.getSource().getLevel();
                level.setChunkForced(0, 0, true);
                station = null;
                current = null;
                basement = ItemStack.EMPTY;
                sealed = ItemStack.EMPTY;
                basin = null;
                ticks = 0;
                index = 0;
                return 1;
            }));
    }

    private void tick(ServerTickEvent.Post event) {
        if (level == null || !level.hasChunkAt(STATION)) return;
        try {
            if (station == null) prepare();
            if (station.getMainNode().isActive()) {
                if (index == 2 && sealed.isEmpty()) verifySealing();
                else if (current == null) supply(STATION_RECIPES.get(index));
                else if (extractProduct() && ++index == STATION_RECIPES.size()) {
                    System.out.println("EXPEDITION_AIRTIGHT_EQUIPMENT_PASS");
                    level = null;
                    return;
                }
            }
            require(++ticks < 340, "timeout at " + STATION_RECIPES.get(Math.min(index, STATION_RECIPES.size() - 1))
                + " progress " + station.getProcessingTime() + " output " + inventory().getStackInSlot(9));
        } catch (Exception error) {
            System.out.println("EXPEDITION_AIRTIGHT_EQUIPMENT_FAIL");
            error.printStackTrace();
            level = null;
        }
    }

    private void prepare() {
        var between = (IntegratedWorkingStationRecipe) recipe(SEALING + "incomplete_air_tight_mechanism");
        require(between.inputItems().stream().anyMatch(input -> input.test(stack(CANISTER))), "gas canister input");
        require(recipe(SEALING + "air_tight_mechanism").getType() == BuiltInRegistries.RECIPE_TYPE.get(
            ResourceLocation.parse("createcraftedbeginning:gas_injection")), "final gas injection");
        checkCraft("basic_chemical_tank", "mekanism:basic_chemical_tank", 1, "mekanism:chemical_tank/basic");
        checkCraft("chemical_cell_housing", "appmek:chemical_cell_housing", 2, "appmek:chemical_cell_housing");
        checkDecoration();
        require(stack(AIR).is(TagKey.create(Registries.ITEM, ResourceLocation.parse("cmi:mechanisms"))), "foundry mold input");
        recipe("expedition:factory/foundry/mechanism_cast_sand");
        recipe("expedition:factory/foundry/mechanism_cast_red_sand");
        for (var machine : MACHINES) {
            var processing = (IntegratedWorkingStationRecipe) recipe(EQUIPMENT + machine);
            require(processing.inputItems().stream().anyMatch(input -> input.test(stack(AIR))), machine + " has no airtight input");
            require(recipe("mekanism:" + machine) instanceof CraftingRecipe, "native recipe " + machine);
        }
        level.setBlockAndUpdate(STATION, block("neoecoae:integrated_working_station").defaultBlockState());
        level.setBlockAndUpdate(STATION.east(), block("ae2:creative_energy_cell").defaultBlockState());
        station = (ECOIntegratedWorkingStationBlockEntity) level.getBlockEntity(STATION);
        require(station != null, "workstation block entity");
    }

    private void checkCraft(String name, String output, int count, String original) {
        var crafting = (ShapedRecipe) recipe(EQUIPMENT + name);
        require(crafting.getIngredients().stream().anyMatch(input -> input.test(stack(AIR))), name + " has no airtight input");
        require(crafting.getIngredients().stream().allMatch(input -> input.isEmpty() || input.getItems().length > 0),
            name + " has an empty ingredient");
        var grid = CraftingInput.of(crafting.getWidth(), crafting.getHeight(), crafting.getIngredients().stream()
            .map(input -> input.isEmpty() ? ItemStack.EMPTY : input.getItems()[0].copy()).toList());
        require(crafting.matches(grid, level), name + " did not match its ingredients");
        require(ItemStack.matches(crafting.assemble(grid, level.registryAccess()), stack(output).copyWithCount(count)), name + " output");
        require(recipe(original) != null, original + " native recipe");
        System.out.println("EXPEDITION_AIRTIGHT_CRAFT " + name + " output=" + count);
    }

    private void checkDecoration() {
        var decorative = (StonecutterRecipe) recipe(EQUIPMENT + "air_tight_machine");
        var input = new SingleRecipeInput(stack(AIR));
        var id = "cmi:air_tight_machine";
        require(decorative.matches(input, level) &&
            ItemStack.matches(decorative.assemble(input, level.registryAccess()), stack(id)), "stonecutting " + id);
        var position = STATION.south(3);
        level.setBlockAndUpdate(position, block(id).defaultBlockState());
        var handler = level.getCapability(Capabilities.ItemHandler.BLOCK, position, Direction.NORTH);
        require(handler != null && handler.getSlots() == 27, "decoration inventory size");
        require(handler.insertItem(0, stack("minecraft:stone"), true).getCount() == 1, "decoration inventory filter");
        require(handler.insertItem(0, stack(AIR), false).isEmpty(), "decoration inventory rejected its mechanism");
        require(ItemStack.matches(handler.extractItem(0, 1, false), stack(AIR)), "decoration inventory extraction");
        System.out.println("EXPEDITION_AIRTIGHT_CRAFT air_tight_machine output=1");
    }

    private void supply(String id) {
        current = (IntegratedWorkingStationRecipe) recipe(id);
        var items = inventory();
        for (var input : current.inputItems()) {
            var sample = Arrays.stream(input.ingredient().getItems()).findFirst()
                .orElseThrow(() -> new IllegalStateException("empty ingredient " + input + " in " + id));
            var supplied = sample.copyWithCount(input.count());
            if (input.test(basement)) supplied = basement.split(input.count());
            if (input.test(sealed)) supplied = sealed.copy();
            require(!supplied.isEmpty(), id + " empty input");
            require(ItemHandlerHelper.insertItemStacked(items, supplied, false).isEmpty(), id + " rejected item " + supplied);
        }
        var fluid = current.inputFluid().ingredient().getStacks()[0].copyWithAmount(current.inputFluid().amount());
        require(station.getFluidCombined().fill(fluid, FluidAction.EXECUTE) == fluid.getAmount(), id + " rejected fluid");
        ticks = 0;
    }

    private boolean extractProduct() {
        var items = inventory();
        for (int slot = 0; slot < items.getSlots(); slot++) {
            if (!ItemStack.matches(items.extractItem(slot, 64, true), current.itemOutput())) continue;
            var result = items.extractItem(slot, 64, false);
            if (index == 0) basement = result;
            if (index == 1) prepareSealing(result);
            System.out.println("EXPEDITION_AIRTIGHT_STATION " + result);
            current = null;
            ticks = 0;
            return true;
        }
        return false;
    }

    private void prepareSealing(ItemStack workpiece) {
        level.setBlockAndUpdate(BASIN, block("create:basin").defaultBlockState());
        level.setBlockAndUpdate(BASIN.above(2), block("createcraftedbeginning:gas_injection_chamber").defaultBlockState());
        basin = (BasinBlockEntity) level.getBlockEntity(BASIN);
        chamber = (GasInjectionChamberBlockEntity) level.getBlockEntity(BASIN.above(2));
        basin.getInputInventory().setStackInSlot(0, workpiece);
        basin.notifyChangeOfContents();
    }

    private void verifySealing() {
        var tank = chamber.getGasTankBehaviour().getPrimaryHandler();
        if (ticks == 15) {
            require(tank.fill(new GasStack(CCBGases.NATURAL_AIR.get(), 15000), GasAction.EXECUTE) == 15000, "air supply");
        }
        var output = basin.getOutputInventory();
        for (int slot = 0; slot < output.getSlots(); slot++) {
            if (!ItemStack.matches(output.getStackInSlot(slot), stack(AIR))) continue;
            require(tank.getStoredAmount() == 14000 && basin.getInputInventory().getStackInSlot(0).isEmpty(), "sealing consumption");
            sealed = output.extractItem(slot, 1, false);
            require(!sealed.isEmpty(), "sealing output not extractable");
            System.out.println("EXPEDITION_AIRTIGHT_SEALED " + sealed);
            ticks = 0;
            return;
        }
    }

    private net.minecraft.world.item.crafting.Recipe<?> recipe(String id) {
        return level.getRecipeManager().byKey(ResourceLocation.parse(id))
            .orElseThrow(() -> new IllegalStateException("missing recipe " + id)).value();
    }

    private IItemHandler inventory() {
        return level.getCapability(Capabilities.ItemHandler.BLOCK, STATION, Direction.UP);
    }

    private static ItemStack stack(String id) {
        return new ItemStack(BuiltInRegistries.ITEM.get(ResourceLocation.parse(id)));
    }

    private static Block block(String id) {
        return BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));
    }

    private static void require(boolean condition, String reason) {
        if (!condition) throw new IllegalStateException(reason);
    }
}
