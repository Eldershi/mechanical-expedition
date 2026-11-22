package expedition.industry;

import com.google.gson.JsonParser;
import com.lowdragmc.mbd2.api.blockentity.ProxyPartBlockEntity;
import com.lowdragmc.mbd2.api.machine.IMultiController;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import com.simibubi.create.content.kinetics.belt.item.BeltConnectorItem;
import com.simibubi.create.content.logistics.funnel.BeltFunnelBlock;
import java.nio.file.Files;
import java.nio.file.Path;
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
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Rotation;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.capabilities.Capabilities;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;
import net.neoforged.neoforge.event.tick.ServerTickEvent;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.capability.IFluidHandler.FluidAction;

public final class HydraulicPressAcceptance {
    private static final String ID = "expedition_industry:hydropress";
    private static final BlockPos CORE = new BlockPos(2, 2, 1);
    private static final BlockPos MOTOR = new BlockPos(2, 7, 3);
    private static final BlockPos BELT_START = new BlockPos(-4, 1, 3);
    private static final BlockPos BELT_END = new BlockPos(0, 1, 3);
    private record Fixture(BlockPos center, Rotation rotation) {
        BlockPos at(int x, int y, int z) { return center.offset(new BlockPos(x, y, z).subtract(CORE).rotate(rotation)); }
        BlockPos at(BlockPos place) { return at(place.getX(), place.getY(), place.getZ()); }
        Direction face(Direction direction) { return rotation.rotate(direction); }
    }
    private final Fixture north = new Fixture(new BlockPos(420, 142, 352), Rotation.NONE);
    private final Fixture east = new Fixture(new BlockPos(452, 142, 352), Rotation.CLOCKWISE_90);
    private final List<Fixture> fixtures = List.of(north, east);
    private long start = -1;
    private int step;
    private boolean pressure, casting;

    public HydraulicPressAcceptance() {
        NeoForge.EVENT_BUS.addListener((RegisterCommandsEvent event) ->
            event.getDispatcher().register(Commands.literal("expeditionpressproof")
                .requires(source -> source.hasPermission(4)).executes(context -> {
                    try {
                        begin(context.getSource().getServer().overworld());
                    } catch (Exception failure) {
                        throw new IllegalStateException("hydraulic press fixture", failure);
                    }
                    return 1;
                })));
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    private void begin(ServerLevel level) throws Exception {
        step = 0;
        pressure = casting = false;
        var layout = JsonParser.parseString(Files.readString(Path.of("brass-fixtures.json")))
            .getAsJsonObject().getAsJsonArray("hydropress");
        for (var f : fixtures) {
            for (int x = -1; x <= 1; x++) for (int z = -1; z <= 1; z++)
                level.setChunkForced((f.center().getX() >> 4)+x, (f.center().getZ() >> 4)+z, true);
            if (f == north) {
                level.removeBlock(f.at(BELT_END), false);
                level.removeBlock(f.at(BELT_START).south(), false);
            }
            level.removeBlock(f.at(MOTOR), false);
            level.removeBlock(f.center(), false);
            level.setBlockAndUpdate(f.center(), state(level, ID + "[facing=north]").rotate(f.rotation()));
            for (var element : layout) {
                var entry = element.getAsJsonArray();
                var pos = new BlockPos(entry.get(0).getAsInt(), entry.get(1).getAsInt(), entry.get(2).getAsInt());
                if (pos.equals(CORE) || pos.equals(MOTOR)) continue;
                level.setBlock(f.at(pos), state(level, entry.get(3).getAsString()).rotate(f.rotation()), Block.UPDATE_CLIENTS);
            }
        }
        start = level.getGameTime();
    }

    private void tick(ServerTickEvent.Post event) {
        if (start < 0) return;
        var level = event.getServer().overworld();
        long t = level.getGameTime() - start;
        try {
            if (step == 0 && t >= 40) {
                for (var f : fixtures) {
                    require(!machine(level,f).isFormedValid(), "missing motor must block formation");
                    level.setBlockAndUpdate(f.at(MOTOR), state(level,"create:mechanical_press"));
                }
                step++;
            }
            if (step == 1 && t >= 105) {
                for (var f : fixtures) verifyPorts(level, f);
                var from = north.at(BELT_START);
                var to = north.at(BELT_END);
                level.setBlockAndUpdate(from.south(), state(level,"create:creative_motor[facing=north]"));
                for (var pos : List.of(from,to)) level.setBlockAndUpdate(pos,state(level,"create:shaft[axis=z]"));
                require(BeltConnectorItem.canConnect(level,from,to), "native belt clearance");
                BeltConnectorItem.createBelts(level,from,to);

                var intake = east.at(2,2,7);
                var pipe = level.getCapability(Capabilities.FluidHandler.BLOCK,intake,east.face(Direction.SOUTH));
                var copper = BuiltInRegistries.FLUID.get(ResourceLocation.parse("modernfoundry:molten_copper"));
                require(pipe.fill(new FluidStack(copper,360),FluidAction.EXECUTE)==360, "source molten copper");
                step++;
            }
            if (step == 2 && t >= 140) {
                var funnel = level.getBlockState(north.at(0,2,3));
                require(funnel.getBlock() instanceof BeltFunnelBlock &&
                        funnel.getValue(BeltFunnelBlock.SHAPE)==BeltFunnelBlock.Shape.RETRACTED, "inline funnel " + funnel);
                var belt = level.getCapability(Capabilities.ItemHandler.BLOCK,north.at(BELT_START),Direction.UP);
                require(belt.insertItem(0,new ItemStack(Items.IRON_BLOCK),false).isEmpty(),"feed native belt");
                step++;
            }
            if (step >= 2 && step < 4) {
                pressure |= machine(level,north).getCustomData().getInt("pressMode") == 1;
                casting |= machine(level,east).getCustomData().getInt("pressMode") == 2;
            }
            if (step == 3 && t >= 415) {
                require(pressure && casting, "distinct synchronized press and casting animations");
                var sheets = take(level,north);
                require(sheets.is(BuiltInRegistries.ITEM.get(ResourceLocation.parse("create:iron_sheet"))) &&
                        sheets.getCount()==9, "native belt fed the iron plate recipe " + sheets);
                var ingots = take(level,east);
                require(ingots.is(Items.COPPER_INGOT)&&ingots.getCount()==4,"copper casting result " + ingots);
                level.destroyBlock(north.at(MOTOR),false);
                step++;
            }
            if (step == 4 && t >= 455) {
                require(!machine(level,north).isFormedValid(), "broken machine must stop");
                require(level.getBlockState(north.at(2,2,7)).is(BuiltInRegistries.BLOCK.get(
                    ResourceLocation.parse("create:fluid_pipe"))), "restore the original fluid pipe");
                level.setBlockAndUpdate(north.at(MOTOR),state(level,"create:mechanical_press"));
                step++;
            }
            if (step == 5 && t >= 540) {
                require(machine(level,north).isFormedValid(), "press must reform after repair");
                require(machine(level,east).isFormedValid(), "rotated press remained formed");
                System.out.println("EXPEDITION_HYDRAULIC_PRESS_COMPLETE");
                start = -1;
            }
        } catch (Exception failure) {
            System.out.println("EXPEDITION_HYDRAULIC_PRESS_FAIL " + failure);
            failure.printStackTrace(System.out);
            start = -1;
        }
    }

    private static void verifyPorts(ServerLevel level, Fixture f) {
        require(machine(level,f).isFormedValid(), "formation " + f + " " + machine(level,f).getMultiblockState().getPos());
        for (var dir : Direction.values()) {
            require((level.getCapability(Capabilities.ItemHandler.BLOCK,f.at(1,2,3),dir)!=null)
                ==(dir==f.face(Direction.WEST)), "item intake " + dir);
            require((level.getCapability(Capabilities.ItemHandler.BLOCK,f.at(4,2,3),dir)!=null)
                ==(dir==f.face(Direction.EAST)), "item output " + dir);
            require((level.getCapability(Capabilities.FluidHandler.BLOCK,f.at(2,2,7),dir)!=null)
                ==(dir==f.face(Direction.SOUTH)), "molten intake " + dir);
            require((level.getCapability(Capabilities.EnergyStorage.BLOCK,f.at(3,2,6),dir)!=null)
                ==(dir==f.face(Direction.EAST)), "FE receiver " + dir);
            require(level.getCapability(Capabilities.ItemHandler.BLOCK,f.center(),dir)==null &&
                level.getCapability(Capabilities.FluidHandler.BLOCK,f.center(),dir)==null &&
                level.getCapability(Capabilities.EnergyStorage.BLOCK,f.center(),dir)==null, "console is for UI only");
        }
        require(level.getBlockEntity(f.at(2,2,7)) instanceof ProxyPartBlockEntity p &&
                p.getOriginalState()!=null,"retain original state under forming");
        require(level.getBlockState(f.at(4,2,6)).is(BuiltInRegistries.BLOCK.get(
            ResourceLocation.parse("createaddition:large_connector"))), "native large connector");
        require(level.getBlockState(f.at(2,4,3)).getCollisionShape(level,f.at(2,4,3)).isEmpty(), "ram clear inside the guard");
        var power = level.getCapability(Capabilities.EnergyStorage.BLOCK,f.at(3,2,6),f.face(Direction.EAST));
        require(power.receiveEnergy(8000,false)==8000 && !power.canExtract(), "FE input");
    }

    private static ItemStack take(ServerLevel level, Fixture f) {
        var port = level.getCapability(Capabilities.ItemHandler.BLOCK,f.at(4,2,3),f.face(Direction.EAST));
        return port.extractItem(0,64,false);
    }

    private static MBDMultiblockMachine machine(ServerLevel level, Fixture f) {
        return (MBDMultiblockMachine) IMultiController.ofController(level,f.center()).orElseThrow();
    }

    private static BlockState state(ServerLevel level,String id) throws Exception {
        return BlockStateParser.parseForBlock(level.registryAccess().lookupOrThrow(Registries.BLOCK),id,false).blockState();
    }

    private static void require(boolean condition,String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
