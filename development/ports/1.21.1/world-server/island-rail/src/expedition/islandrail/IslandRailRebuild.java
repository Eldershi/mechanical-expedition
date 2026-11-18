package expedition.islandrail;

import com.google.gson.JsonParser;
import com.simibubi.create.Create;
import com.simibubi.create.content.trains.graph.EdgePointType;
import com.simibubi.create.content.trains.track.ITrackBlock;
import com.simibubi.create.content.trains.track.TrackBlockEntity;
import com.simibubi.create.content.trains.track.TrackPropagator;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.RegisterCommandsEvent;

public final class IslandRailRebuild {
    public IslandRailRebuild() { NeoForge.EVENT_BUS.addListener(this::register); }

    private void register(RegisterCommandsEvent event) {
        event.getDispatcher().register(Commands.literal("expeditionislandrail")
            .requires(source -> source.hasPermission(4)
                && source.getLevel().dimension().equals(net.minecraft.world.level.Level.OVERWORLD))
            .executes(context -> {
                try {
                    rebuild(context.getSource().getLevel());
                    return 1;
                } catch (Exception failure) {
                    failure.printStackTrace();
                    System.out.println("ISLAND_RAIL_REBUILD_FAILED " + failure);
                    return 0;
                }
            }));
    }

    private void rebuild(ServerLevel level) throws Exception {
        var data = JsonParser.parseString(Files.readString(Path.of("config", "expedition-island-rail", "rail-blocks.json")));
        var tracks = new HashSet<BlockPos>();
        for (var raw : data.getAsJsonObject().getAsJsonArray("rail_blocks")) {
            var state = raw.getAsJsonObject();
            if (!state.get("id").getAsString().equals("create:track")) continue;
            var coords = state.getAsJsonArray("pos");
            var p = new BlockPos(coords.get(0).getAsInt(), coords.get(1).getAsInt(), coords.get(2).getAsInt());
            if (!level.hasChunkAt(p) || !(level.getBlockState(p).getBlock() instanceof ITrackBlock))
                throw new IllegalStateException("Missing retained rail at " + p);
            tracks.add(p);
        }
        if (tracks.isEmpty()) throw new IllegalArgumentException("The retained rail list is empty");
        var manager = Create.RAILWAYS;
        if (!manager.trains.isEmpty() || manager.trackNetworks.values().stream().anyMatch(
            graph -> !graph.getPoints(EdgePointType.STATION).isEmpty() || !graph.getPoints(EdgePointType.SIGNAL).isEmpty())) {
            throw new IllegalStateException("Unexpected trains, stations or signals in the selected repair world");
        }
        int orphaned = 0;
        for (var p : tracks) if (level.getBlockEntity(p) instanceof TrackBlockEntity rail) {
            for (var q : List.copyOf(rail.getConnections().keySet())) {
                if (tracks.contains(q) && level.getBlockEntity(q) instanceof TrackBlockEntity other
                        && other.getConnections().containsKey(p)) continue;
                rail.removeConnection(q);
                orphaned++;
            }
        }
        for (var graph : List.copyOf(manager.trackNetworks.values())) manager.removeGraphAndGroup(graph);
        for (var p : tracks.stream().sorted().toList())
            TrackPropagator.onRailAdded(level, p, level.getBlockState(p));
        manager.markTracksDirty();
        int nodes = manager.trackNetworks.values().stream().mapToInt(g -> g.getNodes().size()).sum();
        if (nodes == 0) throw new IllegalStateException("No Create network was rebuilt");
        System.out.println("ISLAND_RAIL_REBUILD_OK physical=" + tracks.size()
            + " orphaned=" + orphaned + " graphs=" + manager.trackNetworks.size() + " nodes=" + nodes);
    }
}
