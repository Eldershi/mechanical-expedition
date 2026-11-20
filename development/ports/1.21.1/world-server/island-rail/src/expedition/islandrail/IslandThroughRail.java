package expedition.islandrail;

import com.google.gson.Gson;
import com.hxzhitang.tongdarailway.railway.planner.RoutePlanner;
import com.hxzhitang.tongdarailway.structure.TrackPutInfo;
import com.hxzhitang.tongdarailway.util.CurveRoute;
import com.simibubi.create.AllBlocks;
import com.simibubi.create.Create;
import com.simibubi.create.content.trains.entity.TravellingPoint;
import com.simibubi.create.content.trains.graph.TrackEdge;
import com.simibubi.create.content.trains.graph.TrackGraph;
import com.simibubi.create.content.trains.graph.TrackNode;
import com.simibubi.create.content.trains.track.BezierConnection;
import com.simibubi.create.content.trains.track.TrackBlock;
import com.simibubi.create.content.trains.track.TrackBlockEntity;
import com.simibubi.create.content.trains.track.TrackMaterial;
import com.simibubi.create.content.trains.track.TrackShape;
import net.createmod.catnip.data.Couple;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.tags.BlockTags;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

final class IslandThroughRail {
    private static final Vec3 UP = new Vec3(0, 1, 0);

    private record Knot(int x, int y, int z, int dx, int dz) {
        BlockPos block() { return new BlockPos(x, y, z); }
        Vec3 axis() { return new Vec3(dx, 0, dz); }
    }

    private record Point(double x, double y, double z) {
        Vec3 vector() { return new Vec3(x, y, z); }
    }

    private record Route(List<Knot> knots, Point factoryEnd, Point adjoiningEnd, double minimumDistance,
                         boolean clearNaturalLogs) {
        static Route load() throws IOException {
            var path = Path.of("config", "expedition-island-rail", "through-route.json");
            try (var reader = Files.newBufferedReader(path)) {
                var route = new Gson().fromJson(reader, Route.class);
                if (route.knots().size() < 2 || !Double.isFinite(route.minimumDistance())
                    || route.minimumDistance() <= 0) throw new IllegalStateException("Invalid through route");
                for (var knot : route.knots()) {
                    if (Math.abs((long) knot.dx()) > 1 || Math.abs((long) knot.dz()) > 1
                        || (knot.dx() == 0 && knot.dz() == 0)) {
                        throw new IllegalStateException("Invalid horizontal heading at " + knot.block());
                    }
                }
                return route;
            }
        }
    }

    private record Plan(Map<BlockPos, TrackShape> tracks, Map<BlockPos, TrackShape> curveEnds,
                        List<BezierConnection> curves, Set<BlockPos> deck, Set<BlockPos> clearance,
                        Set<BlockPos> piers) {}

    IslandThroughRail() {
        NeoForge.EVENT_BUS.addListener(this::register);
    }

    private void register(RegisterCommandsEvent event) {
        var command = Commands.literal("expeditionrailthrough").requires(source ->
            source.hasPermission(4) && source.getLevel().dimension().equals(Level.OVERWORLD));
        for (var operation : List.of("plan", "build", "check")) {
            command.then(Commands.literal(operation).executes(context -> {
                var source = context.getSource();
                try {
                    var route = Route.load();
                    var plan = plan(route);
                    if (operation.equals("check")) {
                        verify(source.getLevel(), route, plan);
                    } else {
                        var changes = preflight(source.getLevel(), route, plan);
                        if (operation.equals("build")) {
                            apply(source.getLevel(), plan, changes);
                            var chunks = new LinkedHashSet<ChunkPos>();
                            changes.keySet().forEach(pos -> chunks.add(new ChunkPos(pos)));
                            plan.tracks().keySet().forEach(pos -> chunks.add(new ChunkPos(pos)));
                            plan.clearance().forEach(pos -> chunks.add(new ChunkPos(pos)));
                            System.out.println("ISLAND_THROUGH_CORRIDOR_CHUNKS " + chunks);
                        }
                        System.out.printf("ISLAND_THROUGH_%s tracks=%d curves=%d changes=%d%n",
                            operation.toUpperCase(java.util.Locale.ROOT), plan.tracks().size(), plan.curves().size(),
                            changes.size());
                    }
                    return 1;
                } catch (IOException | RuntimeException failure) {
                    source.sendFailure(Component.literal(failure.getMessage()));
                    System.out.println("ISLAND_THROUGH_FAILED " + failure);
                    return 0;
                }
            }));
        }
        event.getDispatcher().register(command);
    }

    private static Plan plan(Route route) {
        var tracks = new LinkedHashMap<BlockPos, TrackShape>();
        var curveEnds = new LinkedHashMap<BlockPos, TrackShape>();
        var curves = new ArrayList<BezierConnection>();
        var deck = new LinkedHashSet<BlockPos>();
        var clearance = new LinkedHashSet<BlockPos>();
        var piers = new LinkedHashSet<BlockPos>();
        var knots = route.knots();
        for (int i = 1; i < knots.size(); i++) {
            var start = knots.get(i - 1);
            var end = knots.get(i);
            var result = new RoutePlanner.ResultWay(new CurveRoute(), new ArrayList<>());
            if (!result.connectWayNormal(Vec3.atLowerCornerOf(start.block()), Vec3.atLowerCornerOf(end.block()),
                start.axis(), end.axis().reverse(), true) || result.trackPutInfos().isEmpty()) {
                throw new IllegalStateException("TongDa rejected the transition " + start + " -> " + end);
            }
            for (var piece : result.trackPutInfos()) {
                addPiece(piece, tracks, curveEnds, curves, deck, clearance, piers);
            }
        }
        clearance.removeAll(deck);
        clearance.removeAll(tracks.keySet());
        deck.removeAll(tracks.keySet());
        return new Plan(tracks, curveEnds, curves, deck, clearance, piers);
    }

    private static void addPiece(TrackPutInfo piece, Map<BlockPos, TrackShape> tracks,
            Map<BlockPos, TrackShape> curveEnds, List<BezierConnection> curves,
            Set<BlockPos> deck, Set<BlockPos> clearance, Set<BlockPos> piers) {
        var first = piece.pos();
        putShape(tracks, first, piece.shape());
        if (piece.bezier() == null) {
            Vec3 axis = piece.shape() == TrackShape.ZO ? new Vec3(0, 0, 1)
                : piece.shape() == TrackShape.PD ? new Vec3(1, 0, 1)
                : piece.shape() == TrackShape.ND ? new Vec3(1, 0, -1) : new Vec3(1, 0, 0);
            corridor(Vec3.atBottomCenterOf(first), axis, deck, clearance);
            return;
        }
        var shape = piece.bezier();
        var last = BlockPos.containing(shape.start().add(shape.endOffset()));
        if (Math.abs(last.getY() - first.getY()) > 15) {
            throw new IllegalStateException("TongDa curve rises more than 15 blocks at " + first);
        }
        putShape(tracks, last, piece.endShape());
        putShape(curveEnds, first, piece.shape());
        putShape(curveEnds, last, piece.endShape());
        // TongDa's spawner attaches each curve at the outer edge of its two track blocks.
        var curve = new BezierConnection(Couple.create(first, last),
            Couple.create(shape.start().add(trackOffset(shape.startAxis())),
                shape.start().add(shape.endOffset()).add(trackOffset(shape.endAxis()))),
            Couple.create(shape.startAxis(), shape.endAxis()), Couple.create(UP, UP), true, false,
            TrackMaterial.ANDESITE);
        curves.add(curve);
        int spans = Math.max(1, (int) Math.ceil(curve.getLength() / 20));
        for (int i = 0; i < spans; i++) {
            var point = curve.getPosition((i + .5) / spans);
            piers.add(BlockPos.containing(point.x, point.y + .35, point.z).below());
        }
        int samples = Math.max(1, (int) Math.ceil(curve.getLength() * 4));
        for (int i = 0; i <= samples; i++) {
            double t = (double) i / samples;
            var point = curve.getPosition(t);
            var tangent = curve.getPosition(Math.min(1, t + .01)).subtract(
                curve.getPosition(Math.max(0, t - .01)));
            corridor(point, tangent, deck, clearance);
        }
    }

    private static Vec3 trackOffset(Vec3 axis) {
        return new Vec3(axisOffset(axis.x), 0, axisOffset(axis.z));
    }

    private static double axisOffset(double coordinate) {
        return Math.abs(coordinate) < 1e-6 ? .5 : coordinate < 0 ? 0 : 1;
    }

    private static void putShape(Map<BlockPos, TrackShape> pieces, BlockPos pos, TrackShape shape) {
        var previous = pieces.putIfAbsent(pos, shape);
        if (previous != null && previous != shape) {
            throw new IllegalStateException("Conflicting planned rail shapes at " + pos);
        }
    }

    private static void corridor(Vec3 point, Vec3 tangent, Set<BlockPos> deck, Set<BlockPos> clearance) {
        var cross = new Vec3(-tangent.z, 0, tangent.x).normalize();
        int railY = (int) Math.floor(point.y + .35);
        for (int side = -1; side <= 1; side++) {
            var offset = point.add(cross.scale(side));
            var pos = BlockPos.containing(offset.x, railY, offset.z);
            deck.add(pos.below());
            for (int headroom = 0; headroom <= 3; headroom++) clearance.add(pos.above(headroom));
        }
    }

    private static Map<BlockPos, BlockState> preflight(ServerLevel level, Route route, Plan plan) {
        for (var end : List.of(route.knots().getFirst(), route.knots().getLast())) {
            var state = stateAt(level, end.block());
            if (!state.is(AllBlocks.TRACK.get()) || state.getValue(TrackBlock.SHAPE) != plan.tracks().get(end.block())) {
                throw new IllegalStateException("Missing original rail or wrong approach at " + end.block());
            }
        }
        for (var curve : plan.curves()) {
            checkExistingCurve(level, curve);
            checkExistingCurve(level, curve.secondary());
        }
        var changes = new LinkedHashMap<BlockPos, BlockState>();
        for (var pos : plan.clearance()) {
            var state = stateAt(level, pos);
            if (state.isAir() || state.is(AllBlocks.FAKE_TRACK.get()) || state.is(AllBlocks.TRACK.get())) continue;
            requireNatural(level, pos, state, route.clearNaturalLogs());
            changes.put(pos, Blocks.AIR.defaultBlockState());
        }
        for (var pos : plan.deck()) {
            var state = stateAt(level, pos);
            if (!state.canBeReplaced() && !state.is(BlockTags.LEAVES)) continue;
            requireNatural(level, pos, state, route.clearNaturalLogs());
            changes.put(pos, Blocks.SMOOTH_STONE.defaultBlockState());
        }
        for (var entry : plan.tracks().entrySet()) {
            var pos = entry.getKey();
            var state = stateAt(level, pos);
            if (state.is(AllBlocks.TRACK.get())) {
                if (state.getValue(TrackBlock.SHAPE) != entry.getValue()) {
                    throw new IllegalStateException("Existing rail uses a different shape at " + pos);
                }
            } else {
                requireNatural(level, pos, state, route.clearNaturalLogs());
            }
        }
        for (var top : plan.piers()) {
            for (var pos = top.below(); ; pos = pos.below()) {
                var state = stateAt(level, pos);
                if (state.isFaceSturdy(level, pos, Direction.UP)) break;
                if (pos.getY() < level.getMinBuildHeight() || top.getY() - pos.getY() > 64) {
                    throw new IllegalStateException("No foundation for railway pier at " + top);
                }
                if (plan.clearance().contains(pos) || plan.tracks().containsKey(pos)) {
                    throw new IllegalStateException("Railway pier meets the track corridor at " + pos);
                }
                requireNatural(level, pos, state, route.clearNaturalLogs());
                changes.putIfAbsent(pos, Blocks.STONE_BRICKS.defaultBlockState());
            }
        }
        return changes;
    }

    private static BlockState stateAt(ServerLevel level, BlockPos pos) {
        if (!level.hasChunkAt(pos)) throw new IllegalStateException("Load the railway corridor at " + pos);
        return level.getBlockState(pos);
    }

    private static void requireNatural(ServerLevel level, BlockPos pos, BlockState state, boolean clearNaturalLogs) {
        if (level.getBlockEntity(pos) != null
            || !(state.canBeReplaced() || state.is(BlockTags.BASE_STONE_OVERWORLD) || state.is(BlockTags.DIRT)
                || state.is(BlockTags.SAND) || state.is(BlockTags.LEAVES) || state.is(Blocks.GRAVEL)
                || (clearNaturalLogs && state.is(BlockTags.LOGS)) || state.is(Blocks.SNOW_BLOCK) || state.is(Blocks.ICE) || state.is(Blocks.CALCITE))) {
            throw new IllegalStateException("Railway corridor would replace an existing block at " + pos + " " + state);
        }
    }

    private static void checkExistingCurve(ServerLevel level, BezierConnection expected) {
        var block = expected.bePositions.getFirst();
        if (level.getBlockEntity(block) instanceof TrackBlockEntity track) {
            var existing = track.getConnections().get(expected.getKey());
            if (existing != null && !existing.equalsSansMaterial(expected)) {
                throw new IllegalStateException("Different curve already joins " + block + " to " + expected.getKey());
            }
        }
    }

    private static void apply(ServerLevel level, Plan plan, Map<BlockPos, BlockState> changes) {
        changes.forEach((pos, state) -> level.setBlock(pos, state, Block.UPDATE_ALL));
        for (var entry : plan.tracks().entrySet()) {
            var pos = entry.getKey();
            var previous = level.getBlockState(pos);
            var state = previous.is(AllBlocks.TRACK.get()) ? previous
                : AllBlocks.TRACK.getDefaultState().setValue(TrackBlock.SHAPE, entry.getValue());
            if (plan.curveEnds().containsKey(pos)) state = state.setValue(TrackBlock.HAS_BE, true);
            if (!state.equals(previous)) level.setBlock(pos, state, Block.UPDATE_ALL);
        }
        for (var curve : plan.curves()) {
            addCurve(level, curve);
            addCurve(level, curve.secondary());
        }
        Create.RAILWAYS.markTracksDirty();
    }

    private static void addCurve(ServerLevel level, BezierConnection curve) {
        if (!(level.getBlockEntity(curve.bePositions.getFirst()) instanceof TrackBlockEntity track)) {
            throw new IllegalStateException("Missing native Create curve anchor " + curve.bePositions.getFirst());
        }
        track.addConnection(curve);
        track.setChanged();
    }

    private record PathStep(TrackNode node, TrackEdge inbound, PathStep previous) {}

    private static void verify(ServerLevel level, Route route, Plan plan) {
        for (var entry : plan.tracks().entrySet()) {
            var state = stateAt(level, entry.getKey());
            if (!state.is(AllBlocks.TRACK.get()) || state.getValue(TrackBlock.SHAPE) != entry.getValue()) {
                throw new IllegalStateException("Missing planned physical rail at " + entry.getKey());
            }
        }
        for (var curve : plan.curves()) {
            requireCurve(level, curve);
            requireCurve(level, curve.secondary());
        }
        for (var graph : Create.RAILWAYS.trackNetworks.values()) {
            var start = closest(graph, route.factoryEnd());
            var finish = closest(graph, route.adjoiningEnd());
            if (start == null || finish == null) continue;
            double outbound = travel(graph, start, finish);
            double inbound = travel(graph, finish, start);
            if (Math.min(outbound, inbound) >= route.minimumDistance()) {
                System.out.printf("ISLAND_THROUGH_VERIFIED outbound=%.2f inbound=%.2f pairedCurves=%d%n",
                    outbound, inbound, plan.curves().size());
                return;
            }
        }
        throw new IllegalStateException("Create could not traverse the factory and adjoining line in both directions");
    }

    private static void requireCurve(ServerLevel level, BezierConnection curve) {
        var origin = curve.bePositions.getFirst();
        if (level.getBlockEntity(origin) instanceof TrackBlockEntity track) {
            var actual = track.getConnections().get(curve.getKey());
            if (actual != null && actual.equalsSansMaterial(curve)) return;
        }
        throw new IllegalStateException("Missing native paired curve " + origin + " -> " + curve.getKey());
    }

    private static TrackNode closest(TrackGraph graph, Point marker) {
        var position = marker.vector();
        return graph.getNodes().stream().filter(node -> node.getDimension().equals(Level.OVERWORLD)
                && node.getLocation().distanceToSqr(position) < 1)
            .min(Comparator.comparingDouble(node -> node.getLocation().distanceToSqr(position)))
            .map(graph::locateNode).orElse(null);
    }

    private static double travel(TrackGraph graph, TrackNode from, TrackNode to) {
        var queue = new ArrayDeque<PathStep>();
        var visited = new HashSet<TrackEdge>();
        queue.add(new PathStep(from, null, null));
        while (!queue.isEmpty()) {
            var step = queue.removeFirst();
            if (step.node() == to) {
                var edges = new ArrayList<TrackEdge>();
                for (var path = step; path.inbound() != null; path = path.previous()) edges.add(path.inbound());
                return movePoint(graph, edges.reversed(), to);
            }
            for (var next : graph.getConnectionsFrom(step.node()).entrySet()) {
                var edge = next.getValue();
                if (step.inbound() != null && (!step.inbound().canTravelTo(edge)
                    || edge.node2 == step.inbound().node1)) continue;
                if (visited.add(edge)) queue.add(new PathStep(next.getKey(), edge, step));
            }
        }
        return 0;
    }

    private static double movePoint(TrackGraph graph, List<TrackEdge> route, TrackNode finish) {
        if (route.isEmpty()) return 0;
        var first = route.getFirst();
        var point = new TravellingPoint(first.node1, first.node2, first, 0, false);
        var turns = new LinkedHashMap<TrackEdge, TrackEdge>();
        for (int i = 1; i < route.size(); i++) turns.put(route.get(i - 1), route.get(i));
        double expected = route.stream().mapToDouble(TrackEdge::getLength).sum();
        double distance = point.travel(graph, expected - .01, (current, options) -> {
            var edge = turns.get(point.edge);
            return options.getSecond().stream().filter(option -> option.getValue() == edge)
                .findFirst().orElseThrow(() -> new IllegalStateException("Train selected another route"));
        });
        return point.node2 == finish && distance >= expected - .02 ? distance : 0;
    }
}
