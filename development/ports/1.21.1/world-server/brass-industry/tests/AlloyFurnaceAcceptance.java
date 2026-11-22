package expedition.industry;

import com.google.gson.JsonParser;
import com.lowdragmc.mbd2.api.blockentity.ProxyPartBlockEntity;
import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.lowdragmc.mbd2.common.trait.item.ItemSlotCapabilityTrait;
import net.minecraft.core.registries.BuiltInRegistries;
import net.neoforged.neoforge.fluids.FluidStack;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.blocks.BlockStateParser;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.Registries;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.fluids.capability.IFluidHandler.FluidAction;

public final class AlloyFurnaceAcceptance {
    private static final String CONTROLLER = "expedition_industry:alloy_furnace";
    private static final BlockPos CORE = new BlockPos(2, 1, 1);
    private record Fixture(BlockPos origin, boolean brass) {
        BlockPos at(int x, int y, int z) { return origin.offset(x, y, z); }
        BlockPos core() { return origin.offset(CORE); }
    }
    private final List<Fixture> fixtures = new ArrayList<>();
    private long start = -1;
    private int phase;

    public AlloyFurnaceAcceptance() {
        NeoForge.EVENT_BUS.addListener((RegisterCommandsEvent event) ->
            event.getDispatcher().register(Commands.literal("expeditionalloyproof")
                .requires(source -> source.hasPermission(4))
                .executes(context -> {
                    begin(context.getSource().getServer().overworld());
                    return 1;
                })));
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void begin(ServerLevel level) {
        fixtures.clear();
        phase = 0;
        try {
            var layouts = JsonParser.parseString(Files.readString(Path.of("brass-fixtures.json"))).getAsJsonObject();
            for (int i = 0; i < 2; i++) {
                Fixture fixture = new Fixture(new BlockPos(324 + 32 * i, 140, 324), i == 1);
                var origin = fixture.origin();
                level.setChunkForced(origin.getX() >> 4, origin.getZ() >> 4, true);
                level.removeBlock(fixture.core(), false);
                for (var entry : layouts.getAsJsonArray("alloy_furnace")) {
                    var cell = entry.getAsJsonArray();
                    var pos = fixture.at(cell.get(0).getAsInt(), cell.get(1).getAsInt(), cell.get(2).getAsInt());
                    String state = cell.get(3).getAsString();
                    if (state.equals(CONTROLLER)) continue;
                    if (fixture.brass()) state = state.replace("create:andesite_funnel", "create:brass_funnel");
                    level.setBlock(pos, parse(level, state), Block.UPDATE_CLIENTS);
                }
                level.setBlockAndUpdate(fixture.core(), parse(level, CONTROLLER+"[facing=north]"));
                fixtures.add(fixture);
            }
        } catch (Exception e) {
            throw new IllegalStateException("alloy fixture", e);
        }
        start = level.getGameTime();
    }

    private void tick(ServerTickEvent.Post event) {
        if (start < 0) return;
        var level = event.getServer().overworld();
        long elapsed = level.getGameTime() - start;
        try {
            if (phase == 0 && elapsed >= 75) {
                for (var f : fixtures) {
                    var machine = machine(level, f);
                    var error = machine.getMultiblockState();
                    require(machine.isFormedValid(), "formation " + f + " at " + error.getPos()
                        + (error.getPos() == null ? "" : " actual " + level.getBlockState(error.getPos())));
                    verifyPorts(level, f);
                    level.setBlockAndUpdate(f.at(2,8,0), Blocks.REDSTONE_BLOCK.defaultBlockState());
                    System.out.println("EXPEDITION_ALLOY_FORM_PORTS_PASS " + f);
                }
                phase = 1;
            }
            if (phase == 1 && elapsed >= 95) {
                for (var f : fixtures) {
                    require(powered(level.getBlockState(f.at(2,8,1))), "north funnel needs to lock");
                    require(!powered(level.getBlockState(f.at(3,8,2))) && !powered(level.getBlockState(f.at(2,8,3))),
                        "redstone leaked into another inlet");
                    require(machine(level, f).isFormedValid(), "redstone must not break formation");
                    level.removeBlock(f.at(2,8,0), false);
                    level.setBlockAndUpdate(f.at(2,7,1), parse(level, "create:depot"));
                }
                phase = 2;
            }
            if (phase == 2 && elapsed >= 120) {
                for (var f : fixtures) {
                    var state = level.getBlockState(f.at(2,8,1));
                    require(block(state).endsWith("_belt_funnel"), "the depot must set belt shape " + state);
                    require(!block(level.getBlockState(f.at(3,8,2))).endsWith("_belt_funnel"),
                        "belt shape leaked into another inlet");
                    require(machine(level, f).isFormedValid(), "belt input must not break formation");
                    level.removeBlock(f.at(2,7,1), false);
                }
                phase = 3;
                System.out.println("EXPEDITION_ALLOY_FUNNEL_STATES_PASS");
            }
            if (phase == 3 && elapsed >= 380) {
                for (var f : fixtures) {
                    var output = level.getCapability(Capabilities.FluidHandler.BLOCK, f.at(0,1,2), Direction.WEST);
                    var molten = output.drain(360, FluidAction.EXECUTE);
                    require(molten.getAmount() == 360, "expected 360 mB after processing, got " + molten);
                    var support = f.at(2,4,2);
                    require(level.getBlockEntity(support) instanceof ProxyPartBlockEntity, "structural proxy");
                    level.destroyBlock(support, false);
                }
                phase = 4;
            }
            if (phase == 4 && elapsed >= 400) {
                for (var f : fixtures) {
                    require(!machine(level, f).isFormedValid(), "must invalidate after removing coil");
                    require(block(level.getBlockState(f.at(0,1,2))).equals("create:fluid_pipe"), "must restore original pipe");
                    require(block(level.getBlockState(f.at(1,4,3))).equals("create:small_scoria_bricks"), "must restore frame");
                    level.setBlockAndUpdate(f.at(2,4,2), parse(level, "immersiveengineering:coil_lv"));
                }
                phase = 5;
            }
            if (phase == 5 && elapsed >= 475) {
                for (var f : fixtures) require(machine(level, f).isFormedValid(), "repair must reform " + f);
                System.out.println("EXPEDITION_ALLOY_COMPLETE");
                start = -1;
            }
        } catch (Exception e) {
            System.out.println("EXPEDITION_ALLOY_FAIL " + e);
            e.printStackTrace(System.out);
            start = -1;
        }
    }

    private static void verifyPorts(ServerLevel level, Fixture f) {
        var receiver = f.at(2,8,2);
        var pipeIn = f.at(2,5,4);
        var pipeOut = f.at(0,1,2);
        var solid = f.at(1,2,4);
        var power = f.at(1,4,3);
        for (var pos : List.of(receiver, pipeIn, pipeOut, solid, power)) {
            require(level.getBlockEntity(pos) instanceof ProxyPartBlockEntity proxy && proxy.getOriginalState() != null,
                "formed port stores its original block " + pos);
        }
        for (var face : Direction.values()) {
            var items = level.getCapability(Capabilities.ItemHandler.BLOCK, receiver, face);
            require((items != null) == (face == Direction.NORTH || face == Direction.EAST || face == Direction.SOUTH),
                "intake exposed on unexpected face " + face + " " + items);
            require((level.getCapability(Capabilities.ItemHandler.BLOCK, solid, face) != null) == (face == Direction.SOUTH),
                "solid output face " + face);
            require((level.getCapability(Capabilities.FluidHandler.BLOCK, pipeIn, face) != null) == (face == Direction.SOUTH),
                "fluid input face " + face);
            require((level.getCapability(Capabilities.FluidHandler.BLOCK, pipeOut, face) != null) == (face == Direction.WEST),
                "fluid output face " + face);
            require((level.getCapability(Capabilities.EnergyStorage.BLOCK, power, face) != null) == (face == Direction.WEST),
                "FE receiver face " + face);
            require(level.getCapability(Capabilities.ItemHandler.BLOCK, f.core(), face) == null
                    && level.getCapability(Capabilities.FluidHandler.BLOCK, f.core(), face) == null
                    && level.getCapability(Capabilities.EnergyStorage.BLOCK, f.core(), face) == null,
                "controller automation face " + face);
        }
        require(block(level.getBlockState(f.at(0,4,3))).equals("createaddition:large_connector"),
            "large connector must remain native");
        var solidOut = level.getCapability(Capabilities.ItemHandler.BLOCK, solid, Direction.SOUTH);
        require(solidOut.insertItem(0, new ItemStack(Items.GLASS), true).getCount() == 1, "solid output must reject input");
        machine(level, f).getTraitByName(ItemSlotCapabilityTrait.class, "item_output").storage.setStackInSlot(0,
            new ItemStack(Items.GLASS, 8));
        require(solidOut.extractItem(0, 8, false).getCount() == 8, "solid output extraction");
        var fluidInput = level.getCapability(Capabilities.FluidHandler.BLOCK, pipeIn, Direction.SOUTH);
        var water = new FluidStack(net.minecraft.world.level.material.Fluids.WATER, 200);
        require(fluidInput.fill(water, FluidAction.SIMULATE) == 200
            && fluidInput.drain(200, FluidAction.SIMULATE).isEmpty(), "fluid input must accept fill only");
        var energy = level.getCapability(Capabilities.EnergyStorage.BLOCK, power, Direction.WEST);
        require(energy.canReceive() && !energy.canExtract(), "FE must be input only");
        for (int i = 0; i < 24; i++) require(energy.receiveEnergy(8000, false) > 0, "FE port failed to charge");
        var input = level.getCapability(Capabilities.ItemHandler.BLOCK, receiver, Direction.NORTH);
        require(input.insertItem(0, new ItemStack(Items.RAW_COPPER, 4), false).isEmpty(), "item port failed to insert");
    }

    private static boolean powered(BlockState state) {
        return state.getOptionalValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.POWERED)
            .orElse(false);
    }

    private static String block(BlockState state) {
        return BuiltInRegistries.BLOCK.getKey(state.getBlock()).toString();
    }

    private static BlockState parse(ServerLevel level, String block) throws Exception {
        return BlockStateParser.parseForBlock(level.registryAccess().lookupOrThrow(Registries.BLOCK), block, false).blockState();
    }

    private static MBDMultiblockMachine machine(ServerLevel level, Fixture fixture) {
        return (MBDMultiblockMachine) IMultiController.ofController(level, fixture.core()).orElseThrow();
    }

    private static void require(boolean valid, String message) {
        if (!valid) throw new IllegalStateException(message);
    }
}
