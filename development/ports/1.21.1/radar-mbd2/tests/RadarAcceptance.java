package expedition.radarproof;

import com.lowdragmc.lowdraglib2.gui.slot.ItemHandlerSlot;
import com.lowdragmc.lowdraglib2.gui.ui.elements.ItemSlot;
import com.lowdragmc.lowdraglib2.gui.ui.elements.ProgressBar;
import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.lowdragmc.mbd2.common.trait.IUIProviderTrait;
import com.lowdragmc.mbd2.common.trait.forgeenergy.CopiableEnergyStorage;
import com.lowdragmc.mbd2.common.trait.forgeenergy.ForgeEnergyCapabilityTrait;
import com.lowdragmc.mbd2.common.trait.item.ItemSlotCapabilityTrait;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Objects;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.items.IItemHandler;

@Mod("expedition_radar_native_probe")
public final class RadarAcceptance {
    private static final BlockPos FIXTURE_ORIGIN = new BlockPos(8, -50, 8);
    private static final BlockPos CONTROLLER = new BlockPos(11, -50, 9);
    private static final BlockPos MODEM = new BlockPos(9, -46, 9);
    private static final int[] POWER = {1_000_000, 2_000_000, 5_000_000, 10_000_000};
    private enum Step { IDLE, PLACING, FORMING, UNPOWERED, PROCESSING, DISASSEMBLING, REFORMING }

    private ServerLevel level;
    private MBDMultiblockMachine machine;
    private BlockState modem;
    private int ticks;
    private Step step = Step.IDLE;
    private int tier;
    private boolean observedWorking;

    public RadarAcceptance() {
        NeoForge.EVENT_BUS.addListener(this::register);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionradarproof").requires(source -> source.hasPermission(4))
            .executes(ctx -> start(ctx.getSource().getLevel())));
    }

    private int start(ServerLevel world) {
        level = world;
        level.setChunkForced(0, 0, true);
        tier = 0;
        advance(Step.PLACING);
        return 1;
    }

    private void tick(ServerTickEvent.Post event) {
        if (step == Step.IDLE) return;
        try {
            switch (step) {
                case PLACING -> assemble();
                case FORMING -> awaitFormation();
                case UNPOWERED -> awaitNoPower();
                case PROCESSING -> awaitOutput();
                case DISASSEMBLING -> awaitRemoval();
                case REFORMING -> awaitReformation();
                case IDLE -> {}
            }
            if (++ticks > 280) throw new IllegalStateException("timeout step=" + step + " tier=" + tier
                + (machine == null ? "" : " formed=" + machine.isFormed() + " state=" + machine.getRecipeLogic().getStatus()
                + " progress=" + machine.getRecipeLogic().getProgress() + " energy=" + energy().getEnergyStored()));
        } catch (Exception error) {
            step = Step.IDLE;
            error.printStackTrace();
            System.out.println("EXPEDITION_RADAR_PROOF_FAILED " + error);
        }
    }

    private void assemble() throws Exception {
        if (!level.hasChunkAt(CONTROLLER)) return;
        for (String row : Files.readAllLines(Path.of("radar-assembly.tsv"))) {
            var fields = row.split("\t");
            var position = FIXTURE_ORIGIN.offset(Integer.parseInt(fields[0]),
                Integer.parseInt(fields[1]), Integer.parseInt(fields[2]));
            var state = block(fields[3]).defaultBlockState();
            require(!state.isAir(), "missing fixture block " + fields[3]);
            level.setBlock(position, state, Block.UPDATE_ALL);
        }
        machine = (MBDMultiblockMachine) IMultiController.ofController(level, CONTROLLER).orElseThrow();
        machine.setFrontFacing(Direction.EAST);
        machine.notifyPatternDirty();
        modem = level.getBlockState(MODEM);
        require(modem.is(block("cmi:modem")), "fixture missing radar modem");
        advance(Step.FORMING);
    }

    private void awaitFormation() {
        if (!machine.isFormedValid()) return;
        require(machine.getMultiblockState().getCache().size() == 51, "unexpected predicate count");
        System.out.println("EXPEDITION_RADAR_FORMED controllerFacing=" + machine.getFrontFacing()
            + " trackedBlocks=" + machine.getMultiblockState().getCache().size());
        var ui = machine.getDefinition().machineSettings().uiTemplate().createUI();
        for (var name : new String[]{"item_input", "item_output", "item_energy"}) {
            var slot = ui.selectId("ui:" + name + "_0", ItemSlot.class)
                .findFirst().orElseThrow(() -> new IllegalStateException("missing slot " + name));
            var trait = itemTrait(name);
            ((IUIProviderTrait)trait.getDefinition()).initTraitUI(trait, ui);
            require(slot.getSlot() instanceof ItemHandlerSlot, "unbound slot " + name);
        }
        require(ui.selectId("ui:forge_energy_storage", ProgressBar.class).count() == 1, "missing energy meter");
        require(ui.selectId("ui:progress_bar", ProgressBar.class).count() == 1, "missing recipe progress");
        System.out.println("EXPEDITION_RADAR_UI_BOUND");
        energy().extractEnergy(energy().getEnergyStored(), false);
        itemTrait("item_input").storage.setStackInSlot(0, ItemStack.EMPTY);
        itemTrait("item_output").storage.setStackInSlot(0, ItemStack.EMPTY);
        itemTrait("item_energy").storage.setStackInSlot(0, ItemStack.EMPTY);
        put(inputItem());
        advance(Step.UNPOWERED);
    }

    private void awaitNoPower() {
        if (ticks < 30) return;
        require(energy().getEnergyStored() == 0, "charge present while checking power gate");
        require(itemTrait("item_output").storage.getStackInSlot(0).isEmpty(), "output without power");
        require(itemTrait("item_input").storage.getStackInSlot(0).is(inputItem()), "unpowered input was consumed");
        System.out.println("EXPEDITION_RADAR_NO_POWER_NO_OUTPUT");
        var battery = new ItemStack(item("mekanism:energy_tablet"));
        var batteryPower = Objects.requireNonNull(battery.getCapability(Capabilities.EnergyStorage.ITEM));
        require(batteryPower.receiveEnergy(2000, false) == 2000, "unable to charge tablet");
        itemTrait("item_energy").storage.setStackInSlot(0, battery);
        charge(POWER[tier] - 2000);
        advance(Step.PROCESSING);
    }

    private void awaitOutput() {
        require(machine.isFormedValid(), "invalid structure during operation");
        observedWorking |= machine.getRecipeLogic().isWorking();
        ItemStack out = itemTrait("item_output").storage.getStackInSlot(0);
        if (out.isEmpty()) return;
        var expected = item("cmi:tier_" + (tier + 1) + "_aviation_cell");
        require(out.is(expected) && out.getCount() == 1, "unexpected output " + out);
        require(observedWorking, "the machine never reported working");
        require(itemTrait("item_input").storage.getStackInSlot(0).isEmpty(), "recipe did not consume input");
        require(energy().getEnergyStored() == 0, "recipe did not consume all " + POWER[tier]);
        if (tier == 0) {
            var installed = itemTrait("item_energy").storage.getStackInSlot(0);
            require(installed.getCapability(Capabilities.EnergyStorage.ITEM).getEnergyStored() == 0,
                "the energy tablet retained energy");
        }
        ItemStack extracted = extractOutput();
        require(ItemStack.matches(extracted, out) && itemTrait("item_output").storage.getStackInSlot(0).isEmpty(),
            "output cannot be extracted through standard capabilities");
        System.out.println("EXPEDITION_RADAR_TIER_COMPLETE tier=" + (tier + 1) + " consumedFE="
            + POWER[tier] + " item=" + BuiltInRegistries.ITEM.getKey(expected) + " ticking=" + observedWorking
            + " recipe=" + machine.getRecipeLogic().getLastOriginRecipe());
        tier++;
        observedWorking = false;
        if (tier < POWER.length) {
            put(extracted.getItem());
            charge(POWER[tier]);
            advance(Step.PROCESSING);
        } else {
            level.removeBlock(MODEM, false);
            advance(Step.DISASSEMBLING);
        }
    }

    private void awaitRemoval() {
        if (machine.isFormedValid()) return;
        System.out.println("EXPEDITION_RADAR_STRICT_DISASSEMBLY");
        level.setBlock(MODEM, modem, Block.UPDATE_ALL);
        advance(Step.REFORMING);
    }

    private void awaitReformation() {
        if (!machine.isFormedValid()) return;
        level.setChunkForced(0, 0, false);
        System.out.println("EXPEDITION_RADAR_NATIVE_FULL_PASS");
        step = Step.IDLE;
    }

    private void charge(int amount) {
        var cap = Objects.requireNonNull(level.getCapability(Capabilities.EnergyStorage.BLOCK, CONTROLLER, Direction.UP));
        require(cap.receiveEnergy(amount, false) == amount, "standard FE input failed for " + amount);
    }

    private IItemHandler items() {
        return Objects.requireNonNull(level.getCapability(Capabilities.ItemHandler.BLOCK, CONTROLLER, Direction.UP));
    }

    private void put(Item input) {
        IItemHandler handler = items();
        for (int i = 0; i < handler.getSlots(); i++) {
            if (handler.insertItem(i, new ItemStack(input), false).isEmpty()) return;
        }
        throw new IllegalStateException("standard item input failed for " + input);
    }

    private ItemStack extractOutput() {
        IItemHandler handler = items();
        for (int i = 0; i < handler.getSlots(); i++) {
            var extracted = handler.extractItem(i, 1, false);
            if (!extracted.isEmpty()) return extracted;
        }
        return ItemStack.EMPTY;
    }

    private CopiableEnergyStorage energy() {
        return machine.getTraitByName(ForgeEnergyCapabilityTrait.class, "forge_energy_storage").getStorage();
    }

    private ItemSlotCapabilityTrait itemTrait(String id) {
        return Objects.requireNonNull(machine.getTraitByName(ItemSlotCapabilityTrait.class, id));
    }

    private Item inputItem() {
        return item(tier == 0 ? "cmi:empty_cell" : "cmi:tier_" + tier + "_aviation_cell");
    }

    private static Item item(String id) {
        return BuiltInRegistries.ITEM.get(ResourceLocation.parse(id));
    }

    private static Block block(String id) {
        return BuiltInRegistries.BLOCK.get(ResourceLocation.parse(id));
    }

    private void advance(Step next) {
        ticks = 0;
        step = next;
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
