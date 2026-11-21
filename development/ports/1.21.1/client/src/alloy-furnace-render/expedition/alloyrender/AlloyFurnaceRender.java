package expedition.alloyrender;

import com.lowdragmc.mbd2.common.machine.MBDMachine;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.client.Minecraft;
import net.minecraft.client.multiplayer.ClientLevel;
import net.minecraft.client.resources.model.ModelResourceLocation;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.state.BlockState;

public final class AlloyFurnaceRender {
    private static final ResourceLocation CONTROLLER = ResourceLocation.parse("expedition_industry:alloy_furnace");
    private static final ModelResourceLocation SHELL = ModelResourceLocation.standalone(
            ResourceLocation.parse("expedition_industry:block/works/alloy_furnace_shell"));
    private static final Set<String> FORMED = Set.of("formed", "working", "waiting", "suspend");
    private static final Map<BlockPos, Placement> PLACEMENTS = new HashMap<>();
    private static volatile Snapshot snapshot = new Snapshot(null, Map.of());

    private record Cell(BlockPos offset, ResourceLocation block) {}
    private record Placement(MBDMachine machine, Direction facing, Map<BlockPos, Block> blocks) {}
    private record Snapshot(ClientLevel level, Map<BlockPos, Block> blocks) {}

    private static final class Layout {
        private static final List<Cell> CELLS = read();

        private static List<Cell> read() {
            var resource = AlloyFurnaceRender.class.getResourceAsStream("/expedition-alloy-render-mask.txt");
            if (resource == null) throw new IllegalStateException("Missing alloy furnace render mask");
            try (var reader = new BufferedReader(new InputStreamReader(resource, StandardCharsets.UTF_8))) {
                return reader.lines().map(line -> {
                    String[] fields = line.split(" ");
                    return new Cell(new BlockPos(Integer.parseInt(fields[0]), Integer.parseInt(fields[1]),
                            Integer.parseInt(fields[2])), ResourceLocation.parse(fields[3]));
                }).toList();
            } catch (IOException ex) {
                throw new IllegalStateException("Cannot read alloy furnace render mask", ex);
            }
        }
    }

    private AlloyFurnaceRender() {}

    public static boolean isVisible(MBDMachine machine) {
        Placement placement = PLACEMENTS.get(machine.getPos());
        return placement != null && placement.machine() == machine && snapshot.level() == machine.getLevel();
    }

    public static boolean hides(BlockPos pos, BlockState state) {
        Snapshot current = snapshot;
        Block block = current.blocks().get(pos);
        return block != null && state.is(block) && current.level() == Minecraft.getInstance().level;
    }

    public static void tick(MBDMachine machine) {
        if (!BuiltInRegistries.BLOCK.getKey(machine.getHolder().getBlockState().getBlock()).equals(CONTROLLER)
                || !(machine.getLevel() instanceof ClientLevel level)) return;
        if (snapshot.level() != level) {
            PLACEMENTS.clear();
            snapshot = new Snapshot(level, Map.of());
        }

        Minecraft client = Minecraft.getInstance();
        var models = client.getModelManager();
        if (!FORMED.contains(machine.getMachineStateName()) || models.getModel(SHELL) == models.getMissingModel()) {
            remove(machine);
            return;
        }
        Direction facing = machine.getFrontFacing().orElse(Direction.NORTH);
        Placement previous = PLACEMENTS.get(machine.getPos());
        if (previous != null && previous.machine() == machine && previous.facing() == facing) return;

        var blocks = new HashMap<BlockPos, Block>();
        for (Cell cell : Layout.CELLS) {
            BlockPos offset = cell.offset();
            int x = offset.getX(), y = offset.getY(), z = offset.getZ();
            BlockPos rotated = switch (facing) {
                case EAST -> new BlockPos(-z, y, x);
                case SOUTH -> new BlockPos(-x, y, -z);
                case WEST -> new BlockPos(z, y, -x);
                default -> offset;
            };
            blocks.put(machine.getPos().offset(rotated), BuiltInRegistries.BLOCK.get(cell.block()));
        }
        PLACEMENTS.put(machine.getPos(), new Placement(machine, facing, blocks));
        refresh();
    }

    public static void remove(MBDMachine machine) {
        if (isVisible(machine)) {
            PLACEMENTS.remove(machine.getPos());
            refresh();
        }
    }

    private static void refresh() {
        Snapshot current = snapshot;
        var next = new HashMap<BlockPos, Block>();
        for (Placement placement : PLACEMENTS.values()) next.putAll(placement.blocks());
        var positions = new HashSet<>(current.blocks().keySet());
        positions.addAll(next.keySet());
        snapshot = new Snapshot(current.level(), Map.copyOf(next));

        var sections = new HashSet<BlockPos>();
        for (BlockPos pos : positions) {
            if (current.blocks().get(pos) != next.get(pos)) sections.add(new BlockPos(pos.getX() >> 4, pos.getY() >> 4, pos.getZ() >> 4));
        }
        var renderer = Minecraft.getInstance().levelRenderer;
        for (BlockPos section : sections) renderer.setSectionDirty(section.getX(), section.getY(), section.getZ());
    }
}
