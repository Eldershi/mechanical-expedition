package expedition.logistics;

import com.google.gson.Gson;
import com.simibubi.create.api.registry.CreateBuiltInRegistries;
import com.simibubi.create.content.kinetics.chainConveyor.ChainConveyorBlockEntity;
import com.simibubi.create.content.logistics.packagePort.PackagePortTarget;
import com.simibubi.create.content.logistics.packagePort.PackagePortTarget.ChainConveyorFrogportTarget;
import com.simibubi.create.content.logistics.packagePort.PackagePortTarget.TrainStationFrogportTarget;
import com.simibubi.create.content.logistics.packagePort.frogport.FrogportBlockEntity;
import com.simibubi.create.content.trains.station.StationBlockEntity;
import com.simibubi.create.infrastructure.config.AllConfigs;
import java.nio.file.Files;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

final class LegacyLogisticsRepair {
    private static final String PLAN_FILE = "expedition-create-logistics-restore.json";
    private static final Gson GSON = new Gson();

    record Plan(int schema, List<Link> links, List<Port> ports) {}
    record Link(String dimension, int[] first, int[] second) {}
    record Port(String dimension, int[] position, String blockEntity, int[] relativePos,
                String type, float chainPos, boolean flipped, int[] connection) {}
    record Position(String dimension, BlockPos pos) {}
    record Edge(String dimension, BlockPos first, BlockPos second) {
        static Edge of(String dimension, BlockPos a, BlockPos b) {
            return a.compareTo(b) < 0 ? new Edge(dimension, a, b) : new Edge(dimension, b, a);
        }
    }

    private final MinecraftServer server;
    private final boolean apply;
    private final Map<String, Integer> result = new LinkedHashMap<>();
    private final Map<ResourceLocation, Set<ChunkPos>> available = new HashMap<>();
    private final Set<Edge> pending = new HashSet<>();
    private final Map<Position, Integer> added = new HashMap<>();

    private LegacyLogisticsRepair(MinecraftServer server, boolean apply) {
        this.server = server;
        this.apply = apply;
    }

    static void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expedition_create_logistics")
            .requires(source -> source.hasPermission(4) && source.getEntity() == null)
            .then(Commands.literal("check").executes(ctx -> run(ctx.getSource(), false)))
            .then(Commands.literal("apply").executes(ctx -> run(ctx.getSource(), true))));
    }

    private static int run(CommandSourceStack source, boolean apply) {
        try (var reader = Files.newBufferedReader(FMLPaths.CONFIGDIR.get().resolve(PLAN_FILE))) {
            var plan = GSON.fromJson(reader, Plan.class);
            validate(plan);
            var repair = new LegacyLogisticsRepair(source.getServer(), apply);
            repair.result.put("package_port_range", AllConfigs.server().logistics.packagePortRange.get());
            repair.result.put("basket_registered", CreateBuiltInRegistries.ARM_INTERACTION_POINT_TYPE
                .containsKey(ResourceLocation.fromNamespaceAndPath("create_central_kitchen", "basket")) ? 1 : 0);
            for (var link : plan.links) repair.link(link);
            for (var port : plan.ports) repair.port(port);
            var summary = (apply ? "Applied " : "Checked ") + repair.result;
            source.sendSuccess(() -> Component.literal(summary), false);
            return 1;
        } catch (Exception failure) {
            source.sendFailure(Component.literal("Create logistics repair: " + failure.getMessage()));
            return 0;
        }
    }

    private static void validate(Plan plan) {
        if (plan == null || plan.schema != 1) throw new IllegalArgumentException("Unsupported plan format");
        Set<Edge> uniqueLinks = new HashSet<>();
        for (var link : plan.links) {
            ResourceLocation.parse(link.dimension);
            var a = pos(link.first);
            var b = pos(link.second);
            if (a.equals(b) || !uniqueLinks.add(Edge.of(link.dimension, a, b)))
                throw new IllegalArgumentException("Invalid or duplicate chain link");
        }
        Set<Position> uniquePorts = new HashSet<>();
        for (var port : plan.ports) {
            ResourceLocation.parse(port.dimension);
            if (!uniquePorts.add(new Position(port.dimension, pos(port.position))))
                throw new IllegalArgumentException("Duplicate frogport in plan");
            pos(port.relativePos);
            if (port.connection != null) pos(port.connection);
            if (!Set.of("create:package_frogport", "fluidlogistics:copper_frogport").contains(port.blockEntity)
                || !Set.of("chain_conveyor", "train_station").contains(port.type)
                || !Float.isFinite(port.chainPos))
                throw new IllegalArgumentException("Invalid frogport binding");
        }
    }

    private static BlockPos pos(int[] value) {
        if (value == null || value.length != 3) throw new IllegalArgumentException("Expected a position with three coordinates");
        return new BlockPos(value[0], value[1], value[2]);
    }

    private void count(String label) {
        result.merge(label, 1, Integer::sum);
    }

    private ServerLevel dimension(String id) {
        return server.getLevel(ResourceKey.create(Registries.DIMENSION, ResourceLocation.parse(id)));
    }

    private BlockEntity blockEntity(ServerLevel level, BlockPos pos) {
        if (level == null || level.isOutsideBuildHeight(pos)) return null;
        var chunk = new ChunkPos(pos);
        var known = available.computeIfAbsent(level.dimension().location(), ignored -> new HashSet<>());
        if (known.add(chunk) && !level.getChunkSource().hasChunk(chunk.x, chunk.z)
            && level.getChunkSource().chunkMap.read(chunk).join().isEmpty()) {
            known.remove(chunk);
            return null;
        }
        return level.getBlockEntity(pos);
    }

    private void link(Link link) {
        var level = dimension(link.dimension);
        var a = pos(link.first);
        var b = pos(link.second);
        if (!(blockEntity(level, a) instanceof ChainConveyorBlockEntity first)
            || !(blockEntity(level, b) instanceof ChainConveyorBlockEntity second)) {
            count("links_missing_conveyor");
            return;
        }
        boolean firstMissing = !first.connections.contains(b.subtract(a));
        boolean secondMissing = !second.connections.contains(a.subtract(b));
        if (!firstMissing && !secondMissing) {
            count("links_already_restored");
            return;
        }
        int limit = AllConfigs.server().kinetics.maxChainConveyorConnections.get();
        int length = AllConfigs.server().kinetics.maxChainConveyorLength.get();
        var firstPosition = new Position(link.dimension, a);
        var secondPosition = new Position(link.dimension, b);
        if (a.distSqr(b) > (double) length * length
            || (firstMissing && first.connections.size() + added.getOrDefault(firstPosition, 0) >= limit)
            || (secondMissing && second.connections.size() + added.getOrDefault(secondPosition, 0) >= limit)) {
            count("links_outside_limits");
            return;
        }
        pending.add(Edge.of(link.dimension, a, b));
        if (apply) {
            if (firstMissing) first.addConnectionTo(b);
            if (secondMissing) second.addConnectionTo(a);
        } else {
            if (firstMissing) added.merge(firstPosition, 1, Integer::sum);
            if (secondMissing) added.merge(secondPosition, 1, Integer::sum);
        }
        count(apply ? "links_restored" : "links_ready");
    }

    private void port(Port port) {
        var level = dimension(port.dimension);
        var position = pos(port.position);
        if (!(blockEntity(level, position) instanceof FrogportBlockEntity frog)
            || !BuiltInRegistries.BLOCK_ENTITY_TYPE.getKey(frog.getType()).toString().equals(port.blockEntity)) {
            count("ports_missing_frogport");
            return;
        }
        var relative = pos(port.relativePos);
        var endpoint = position.offset(relative);
        var connection = port.connection == null ? null : pos(port.connection);
        PackagePortTarget target = switch (port.type) {
            case "chain_conveyor" -> new ChainConveyorFrogportTarget(relative, port.chainPos, connection, port.flipped);
            case "train_station" -> new TrainStationFrogportTarget(relative);
            default -> throw new IllegalArgumentException("Unknown frogport target");
        };
        if (frog.target != null) {
            count(sameBinding(frog.target, target) ? "ports_already_restored" : "ports_existing_binding");
            return;
        }
        var destination = blockEntity(level, endpoint);
        if ((target instanceof ChainConveyorFrogportTarget && !(destination instanceof ChainConveyorBlockEntity))
            || (target instanceof TrainStationFrogportTarget && !(destination instanceof StationBlockEntity))) {
            count("ports_missing_target");
            return;
        }
        if (connection != null && destination instanceof ChainConveyorBlockEntity conveyor
            && !conveyor.connections.contains(connection)
            && !pending.contains(Edge.of(port.dimension, endpoint, endpoint.offset(connection)))) {
            count("ports_missing_chain");
            return;
        }
        if (apply) {
            frog.target = target;
            target.register(frog, level, position);
            frog.notifyUpdate();
        }
        count(apply ? "ports_restored" : "ports_ready");
    }

    private static boolean sameBinding(PackagePortTarget current, PackagePortTarget original) {
        if (current instanceof ChainConveyorFrogportTarget a && original instanceof ChainConveyorFrogportTarget b) {
            if (a.relativePos.equals(b.relativePos) && Objects.equals(a.connection, b.connection))
                return Math.abs(a.chainPos - b.chainPos) < 0.01f;
            // Create may move a port to the opposite endpoint of the same span when rotation reverses.
            return a.connection != null && b.connection != null && a.flipped != b.flipped
                && a.relativePos.offset(a.connection).equals(b.relativePos)
                && b.relativePos.offset(b.connection).equals(a.relativePos);
        }
        return current.getClass().equals(original.getClass()) && current.relativePos.equals(original.relativePos);
    }
}
