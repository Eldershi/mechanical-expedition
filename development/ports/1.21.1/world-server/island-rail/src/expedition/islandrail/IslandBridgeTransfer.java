package expedition.islandrail;

import com.google.gson.Gson;
import com.mojang.authlib.GameProfile;
import com.simibubi.create.AllBlocks;
import com.simibubi.create.Create;
import com.simibubi.create.content.trains.graph.TrackEdge;
import com.simibubi.create.content.trains.graph.TrackGraph;
import com.simibubi.create.content.trains.graph.TrackNode;
import com.simibubi.create.content.trains.track.BezierConnection;
import com.simibubi.create.content.trains.track.ITrackBlock;
import com.simibubi.create.content.trains.track.TrackBlock;
import com.simibubi.create.content.trains.track.TrackBlockEntity;
import com.simibubi.create.content.trains.track.TrackBlockItem;
import com.simibubi.create.content.trains.track.TrackShape;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.HashSet;
import java.util.List;
import java.util.UUID;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.tags.BlockTags;
import net.minecraft.tags.FluidTags;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.item.context.UseOnContext;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.StairBlock;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.FakePlayer;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

public final class IslandBridgeTransfer {
    private record Position(int x, int y, int z) {
        BlockPos block() {
            return new BlockPos(x, y, z);
        }
    }

    private record Point(double x, double y, double z) {
        Vec3 vector() {
            return new Vec3(x, y, z);
        }
    }

    private record Curve(Position first, Position second) {}
    private record Stair(Position position, Direction ascent) {}

    private record Route(Point origin, Point existingTrackEnd, Point landTrackEnd, List<Position> gapAnchors,
                         TrackShape gapShape, List<Curve> retainedCurves, List<Position> shoreAnchors,
                         TrackShape shoreShape, List<Position> rockWitnesses, int deckHalfWidth,
                         List<Position> piers, List<Position> landingDeck, List<Stair> landingStairs) {
        static Route load() {
            var path = Path.of("config", "expedition-island-rail", "bridge-route.json");
            try (var reader = Files.newBufferedReader(path)) {
                var route = new Gson().fromJson(reader, Route.class);
                if (route.gapAnchors.size() < 2 || route.shoreAnchors.size() < 2 || route.rockWitnesses.size() < 2
                    || route.deckHalfWidth < 1 || route.deckHalfWidth > 5) {
                    throw new IllegalArgumentException("Invalid bridge route or deck width in " + path);
                }
                route.shoreSpan();
                return route;
            } catch (IOException e) {
                throw new IllegalStateException("Could not read bridge coordinates from " + path, e);
            }
        }

        List<BlockPos> gap() {
            return gapAnchors.stream().map(Position::block).toList();
        }

        List<BlockPos> shore() {
            return shoreAnchors.stream().map(Position::block).toList();
        }

        List<BlockPos> shoreSpan() {
            var positions = shore();
            var start = positions.getFirst();
            var end = positions.getLast();
            var heading = Direction.getNearest(end.getX() - start.getX(), 0, end.getZ() - start.getZ());
            int distance = (int) end.distManhattan(start);
            for (int i = 1; i < positions.size(); i++) {
                var from = positions.get(i - 1);
                var to = positions.get(i);
                int length = (int) to.distManhattan(from);
                if (length < 1 || length > 32 || !from.relative(heading, length).equals(to)) {
                    throw new IllegalArgumentException("Shore rail needs ascending coordinates along one level cardinal axis");
                }
            }
            return java.util.stream.IntStream.rangeClosed(0, distance).mapToObj(i -> start.relative(heading, i)).toList();
        }
    }

    public IslandBridgeTransfer() {
        NeoForge.EVENT_BUS.addListener(this::register);
    }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionrailbridge").requires(source -> source.hasPermission(4)
            && source.getLevel().dimension().equals(net.minecraft.world.level.Level.OVERWORLD))
            .then(Commands.literal("build").executes(context -> {
                build(context.getSource().getLevel(), Route.load());
                return 1;
            })).then(Commands.literal("check").executes(context -> {
                var route = Route.load();
                check(context.getSource().getLevel(), route, route.existingTrackEnd().vector());
                return 1;
            })).then(Commands.literal("land").executes(context -> {
                land(context.getSource().getLevel(), Route.load());
                return 1;
            })).then(Commands.literal("check-land").executes(context -> {
                checkLand(context.getSource().getLevel(), Route.load());
                return 1;
            })));
    }

    private static void build(ServerLevel level, Route route) {
        var waypoints = route.gap();
        for (var pos : waypoints) {
            if (!level.hasChunkAt(pos)) throw new IllegalStateException("Missing bridge chunk " + pos);
        }
        requireRail(level, waypoints.getFirst());
        requireRail(level, waypoints.getLast());
        verifyOriginalCurves(level, route);
        for (BlockPos pos : waypoints.subList(1, waypoints.size() - 1)) {
            placeRailAnchor(level, pos, route.gapShape());
        }
        var player = builder(level);
        for (int i = 0; i < waypoints.size() - 1; i++) {
            connect(level, player, waypoints.get(i), waypoints.get(i + 1));
        }
        System.out.println("ISLAND_BRIDGE_GAP_FILLED");
    }

    private static FakePlayer builder(ServerLevel level) {
        return new FakePlayer(level, new GameProfile(
            UUID.fromString("15ef69f3-e36d-4d4f-a9da-5814ed142563"), "ExpeditionRailQA")) {
            @Override
            public boolean isCreative() {
                return true;
            }

            @Override
            public void displayClientMessage(net.minecraft.network.chat.Component message, boolean overlay) {
                System.out.println("ISLAND_BRIDGE_CREATE_STATUS " + message.getString());
            }
        };
    }

    private static void placeRailAnchor(ServerLevel level, BlockPos pos, TrackShape shape) {
        var previous = level.getBlockState(pos);
        if (previous.getBlock() instanceof ITrackBlock) return;
        if (!level.hasChunkAt(pos) || !previous.canBeReplaced()) throw new IllegalStateException("Unavailable waypoint " + pos);
        level.setBlock(pos, AllBlocks.TRACK.getDefaultState().setValue(TrackBlock.SHAPE, shape), Block.UPDATE_ALL);
    }

    private static void connect(ServerLevel level, FakePlayer player, BlockPos first, BlockPos second) {
        var stack = AllBlocks.TRACK.asStack();
        var direction = Vec3.atCenterOf(second).subtract(Vec3.atCenterOf(first)).normalize();
        if (!TrackBlockItem.select(level, first, direction, stack)) {
            throw new IllegalStateException("Could not select " + first);
        }
        player.setYRot((float) Math.toDegrees(Math.atan2(-direction.x, direction.z)));
        player.setItemInHand(InteractionHand.MAIN_HAND, stack);
        var hit = new BlockHitResult(Vec3.atCenterOf(second), Direction.UP, second, false);
        var result = stack.getItem().useOn(new UseOnContext(player, InteractionHand.MAIN_HAND, hit));
        if (result == InteractionResult.FAIL) throw new IllegalStateException("Native Create connection rejected " + first + " -> " + second);
        System.out.println("ISLAND_BRIDGE_NATIVE_PLACED " + first + " -> " + second);
    }

    private static void land(ServerLevel level, Route route) {
        var anchors = route.shore();
        var span = route.shoreSpan();
        var start = anchors.getFirst();
        var heading = Direction.getNearest(anchors.getLast().getX() - start.getX(), 0,
            anchors.getLast().getZ() - start.getZ());
        requireRail(level, start);
        requireRock(level, route);
        checkClearance(level, route);
        var stairs = Blocks.STONE_STAIRS.defaultBlockState();
        for (var stair : route.landingStairs()) {
            var position = stair.position().block();
            if (!level.hasChunkAt(position) || !level.getBlockState(position).canBeReplaced()) {
                throw new IllegalStateException("Shore steps would replace solid terrain at " + position);
            }
        }
        for (var anchor : anchors.subList(1, anchors.size())) {
            placeRailAnchor(level, anchor, route.shoreShape());
        }
        var player = builder(level);
        for (int i = 1; i < anchors.size(); i++) {
            connect(level, player, anchors.get(i - 1), anchors.get(i));
        }
        for (var rail : span) {
            requireRail(level, rail);
            for (int width = -route.deckHalfWidth(); width <= route.deckHalfWidth(); width++) {
                addDeck(level, rail.below().relative(heading.getClockWise(), width));
            }
        }
        for (var deck : route.landingDeck()) {
            addDeck(level, deck.block());
        }
        for (var pier : route.piers()) {
            addPier(level, pier.block());
        }
        for (var stair : route.landingStairs()) {
            var position = stair.position().block();
            addPier(level, position.below());
            level.setBlock(position, stairs.setValue(StairBlock.FACING, stair.ascent()), Block.UPDATE_ALL);
        }
        System.out.println("ISLAND_BRIDGE_DRY_LANDFALL");
    }

    private static void requireRock(ServerLevel level, Route route) {
        for (var witness : route.rockWitnesses()) {
            var position = witness.block();
            var state = level.getBlockState(position);
            if (!state.is(BlockTags.BASE_STONE_OVERWORLD) && !state.is(Blocks.CALCITE) && !state.is(Blocks.TUFF)) {
                throw new IllegalStateException("Rock foundation missing at " + position + " " + state);
            }
        }
    }

    private static void checkClearance(ServerLevel level, Route route) {
        var span = route.shoreSpan();
        var offset = span.getFirst().getX() == span.getLast().getX() ? Direction.EAST : Direction.SOUTH;
        for (var rail : span) {
            if (!level.hasChunkAt(rail)) throw new IllegalStateException("Missing bridge chunk at " + rail);
            for (int side = -1; side <= 1; side++) {
                for (int height = 0; height <= 4; height++) {
                    var position = rail.above(height).relative(offset, side);
                    var state = level.getBlockState(position);
                    if (state.isAir() || (height == 0 && side == 0 && state.getBlock() instanceof ITrackBlock)
                        || state.is(Blocks.SNOW)) continue;
                    throw new IllegalStateException("Obstruction in the new train corridor at " + position + " " + state);
                }
            }
        }
    }

    private static void addDeck(ServerLevel level, BlockPos pos) {
        var state = level.getBlockState(pos);
        if (!level.hasChunkAt(pos)) throw new IllegalStateException("Missing new bridge support chunk " + pos);
        if (state.isAir() || state.is(Blocks.SNOW) || level.getFluidState(pos).is(FluidTags.WATER)) {
            level.setBlock(pos, Blocks.SMOOTH_STONE.defaultBlockState(), Block.UPDATE_ALL);
        }
    }

    private static void addPier(ServerLevel level, BlockPos top) {
        for (var pos = top; pos.getY() >= -40; pos = pos.below()) {
            var state = level.getBlockState(pos);
            boolean surfaceIce = state.is(Blocks.ICE) || state.is(Blocks.FROSTED_ICE);
            if (!surfaceIce && state.isFaceSturdy(level, pos, Direction.UP)
                && !level.getFluidState(pos).is(FluidTags.WATER)) return;
            if (state.isAir() || state.canBeReplaced() || surfaceIce || level.getFluidState(pos).is(FluidTags.WATER)) {
                level.setBlock(pos, Blocks.STONE_BRICKS.defaultBlockState(), Block.UPDATE_ALL);
            } else {
                throw new IllegalStateException("Unexpected existing block in new pier " + pos + " " + state);
            }
        }
        throw new IllegalStateException("No seabed found under the new pier " + top);
    }

    private static void checkLand(ServerLevel level, Route route) {
        requireRock(level, route);
        checkClearance(level, route);
        for (var rail : route.shoreSpan()) {
            requireRail(level, rail);
            if (level.getBlockState(rail.below()).isAir()) throw new IllegalStateException("Bridge deck missing at " + rail);
        }
        check(level, route, route.landTrackEnd().vector());
        System.out.println("ISLAND_BRIDGE_LANDFALL_CONNECTED");
    }

    private static void check(ServerLevel level, Route route, Vec3 target) {
        verifyOriginalCurves(level, route);
        for (var pos : route.gap()) requireRail(level, pos);
        for (var graph : Create.RAILWAYS.trackNetworks.values()) {
            var inside = nearest(graph, route.origin().vector());
            var outside = nearest(graph, target);
            if (inside == null || outside == null) continue;
            var outbound = traverse(graph, inside, outside);
            var inbound = traverse(graph, outside, inside);
            if (outbound != null && inbound != null) {
                System.out.println("ISLAND_BRIDGE_NATIVE_CONNECTED out=" + outbound + " back=" + inbound);
                return;
            }
        }
        throw new IllegalStateException("The saved factory and outside bridge ends are not traversable in both directions");
    }

    private static void requireRail(ServerLevel level, BlockPos pos) {
        if (!level.hasChunkAt(pos) || !(level.getBlockState(pos).getBlock() instanceof ITrackBlock)) {
            throw new IllegalStateException("Physical Create rail missing at " + pos);
        }
    }

    private static void verifyOriginalCurves(ServerLevel level, Route route) {
        for (var curve : route.retainedCurves()) {
            requireCurve(level, curve.first().block(), curve.second().block());
        }
    }

    private static BezierConnection requireCurve(ServerLevel level, BlockPos from, BlockPos to) {
        if (level.getBlockEntity(from) instanceof TrackBlockEntity first
            && level.getBlockEntity(to) instanceof TrackBlockEntity second
            && first.getConnections().containsKey(to) && second.getConnections().containsKey(from)) {
            return first.getConnections().get(to);
        }
        throw new IllegalStateException("Paired bridge curve missing " + from + " -> " + to);
    }

    private static TrackNode nearest(TrackGraph graph, Vec3 point) {
        return graph.getNodes().stream().filter(node -> node.getLocation().distanceToSqr(point) < 1.0)
            .min(java.util.Comparator.comparingDouble(node -> node.getLocation().distanceToSqr(point)))
            .map(graph::locateNode).orElse(null);
    }

    private record Step(TrackNode node, TrackEdge incoming, int edges, double length) {}

    private static Step traverse(TrackGraph graph, TrackNode start, TrackNode end) {
        var queue = new ArrayDeque<Step>();
        var visited = new HashSet<TrackEdge>();
        queue.add(new Step(start, null, 0, 0));
        while (!queue.isEmpty()) {
            var step = queue.removeFirst();
            if (step.node == end) return step;
            for (var connection : graph.getConnectionsFrom(step.node).entrySet()) {
                var edge = connection.getValue();
                if (step.incoming != null && (edge.node2 == step.incoming.node1 || !step.incoming.canTravelTo(edge))) continue;
                if (visited.add(edge)) queue.add(new Step(connection.getKey(), edge, step.edges + 1, step.length + edge.getLength()));
            }
        }
        return null;
    }
}
