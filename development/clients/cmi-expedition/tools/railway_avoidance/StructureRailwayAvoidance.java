package expedition.railway;

import com.xkmxz.tongdarailway_for_forge.Config;
import com.xkmxz.tongdarailway_for_forge.railway.RailwayBuilder;
import com.xkmxz.tongdarailway_for_forge.railway.RailwayMap;
import com.xkmxz.tongdarailway_for_forge.railway.RegionPos;
import com.xkmxz.tongdarailway_for_forge.structure.RailwayTemplate;
import com.xkmxz.tongdarailway_for_forge.structure.RoadbedManager;
import com.xkmxz.tongdarailway_for_forge.structure.StationManager;
import com.xkmxz.tongdarailway_for_forge.util.CurveRoute;
import com.xkmxz.tongdarailway_for_forge.util.ModSaveData;
import expedition.railway.mixin.StationSizeAccessor;
import java.util.*;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.LevelHeightAccessor;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraftforge.server.ServerLifecycleHooks;

/** Reject a new candidate before vanilla stores its start or places any pieces. */
public final class StructureRailwayAvoidance {
    private static final Map<RailwayMap, Index> INDEXES = Collections.synchronizedMap(new WeakHashMap<>());
    private static final Map<ChunkGenerator, Boolean> ENABLED = Collections.synchronizedMap(new WeakHashMap<>());
    public static final AtomicLong checked = new AtomicLong();
    public static final AtomicLong rejected = new AtomicLong();
    private StructureRailwayAvoidance() {}

    public static boolean conflicts(StructureStart candidate, ChunkGenerator generator,
                                    long seed, LevelHeightAccessor height) {
        if (candidate == null || !candidate.m_73603_() || !(height instanceof ChunkAccess chunk)) return false;
        return conflictsBox(candidate.m_73601_(), generator, seed, chunk);
    }

    public static boolean conflictsBox(BoundingBox box, ChunkGenerator generator,
                                       long seed, ChunkAccess chunk) {
        MinecraftServer server = ServerLifecycleHooks.getCurrentServer();
        if (server == null) return false;
        ServerLevel level = server.m_129880_(Level.f_46428_);
        // Identity also excludes other dimensions that happen to share a seed.
        if (level == null || generator != level.m_7726_().m_8481_() || seed != level.m_7328_()) return false;
        boolean enabled;
        synchronized (ENABLED) {
            enabled = ENABLED.computeIfAbsent(generator, g -> g.m_62218_().m_207840_().stream().anyMatch(b ->
                g.m_223131_(b).m_47818_().stream().anyMatch(step -> step.m_203614_().anyMatch(f ->
                    f.m_203543_().map(key -> key.m_135782_().toString().equals("tongdarailway_for_forge:railway_and_station")).orElse(false)))));
        }
        if (!enabled) return false;
        if (RoadbedManager.ground.isEmpty() && RoadbedManager.tunnel.isEmpty() && RoadbedManager.bridge.isEmpty()) return false;
        checked.incrementAndGet();
        // The unchanged upstream planner only asks this adapter for server,
        // level, seed and sea level. It samples generator noise/biomes, never
        // requests a chunk with create=true, and never places world blocks.
        WorldGenRegion planning = new WorldGenRegion(level, List.of(chunk), chunk.m_6415_(), 0);
        // DimensionDataStorage itself is not concurrent. Publish the one saved
        // data entry before parallel planning uses its concurrent region maps.
        synchronized (level.m_8895_()) { ModSaveData.get(level); }
        RailwayBuilder builder = RailwayBuilder.getInstance(seed, planning);
        int size = Config.chunkGroupSize * 16;
        int padding = 32;
        var allStations = new ArrayList<>(StationManager.normalStation.values());
        allStations.addAll(StationManager.undergroundStation.values());
        for (var station : allStations) {
            var dim = ((StationSizeAccessor)(Object)station).expedition$size();
            padding = Math.max(padding, Math.max(dim.m_123341_(), dim.m_123343_()) + 2);
        }
        int x0 = Math.floorDiv(box.m_162395_() - padding, size);
        int z0 = Math.floorDiv(box.m_162398_() - padding, size);
        int x1 = Math.floorDiv(box.m_162399_() + padding, size);
        int z1 = Math.floorDiv(box.m_162401_() + padding, size);
        for (int x = x0; x <= x1; x++) for (int z = z0; z <= z1; z++) {
            RegionPos region = new RegionPos(x, z);
            builder.generateRailway(region);
            RailwayMap map = builder.regionRailways.get(region);
            if (map == null) throw new IllegalStateException("Tongda railway plan unavailable for " + region);
            Index index;
            synchronized (INDEXES) { index = INDEXES.computeIfAbsent(map, Index::new); }
            if (index.intersects(box)) { rejected.incrementAndGet(); return true; }
        }
        return false;
    }

    /** Inclusive block-volume intersection, shared with the isolated probe. */
    public record Volume(double x0, double y0, double z0, double x1, double y1, double z1) {
        public boolean intersects(BoundingBox b) {
            return x1 >= b.m_162395_() && x0 <= b.m_162399_()
                && y1 >= b.m_162396_() && y0 <= b.m_162400_()
                && z1 >= b.m_162398_() && z0 <= b.m_162401_();
        }
    }

    private static final class Index {
        final Map<Long, List<Volume>> chunks = new HashMap<>();
        final List<Volume> stations = new ArrayList<>();
        Index(RailwayMap map) {
            double radius = 5, low = -3, high = 3;
            List<RailwayTemplate> templates = new ArrayList<>();
            templates.addAll(RoadbedManager.ground.values());
            templates.addAll(RoadbedManager.tunnel.values());
            templates.addAll(RoadbedManager.bridge.values());
            for (RailwayTemplate t : templates) {
                radius = Math.max(radius, Math.hypot(t.getDepth() / 2.0 + 1, 3) + 2);
                low = Math.min(low, t.getLowerBound() - 3);
                high = Math.max(high, t.getUpperBound() + 3);
            }
            // Tongda flattens the placement frame to horizontal tangent,
            // vertical normal. These bounds include air excavation, the full
            // roadbed/bridge/tunnel template, and a two-block sampling margin.
            Set<CurveRoute.CompositeCurve> curves = Collections.newSetFromMap(new IdentityHashMap<>());
            map.routeMap.values().forEach(curves::addAll);
            for (CurveRoute.CompositeCurve curve : curves) for (CurveRoute.CurveSegment segment : curve.getSegments()) {
                int count = Math.max(1, (int)Math.ceil(segment.getLength() * 2));
                for (int i = 0; i <= count; i++) {
                    CurveRoute.Point3D p = segment.evaluate((double)i / count);
                    add(new Volume(p.x-radius, p.y+low, p.z-radius, p.x+radius, p.y+high, p.z+radius), map);
                }
            }
            for (var s : map.stations) {
                if (s.stationStructure() == null) continue;
                var dim = ((StationSizeAccessor)(Object)s.stationStructure()).expedition$size();
                var pos = s.placePos();
                stations.add(new Volume(pos.m_123341_()-2, pos.m_123342_()-2, pos.m_123343_()-2,
                    pos.m_123341_()+dim.m_123341_()+2, pos.m_123342_()+dim.m_123342_()+2,
                    pos.m_123343_()+dim.m_123343_()+2));
            }
        }
        void add(Volume v, RailwayMap map) {
            for (int x = ((int)Math.floor(v.x0)) >> 4; x <= ((int)Math.floor(v.x1)) >> 4; x++)
                for (int z = ((int)Math.floor(v.z0)) >> 4; z <= ((int)Math.floor(v.z1)) >> 4; z++)
                    if (map.routeMap.containsKey(new ChunkPos(x,z)))
                        chunks.computeIfAbsent(ChunkPos.m_45589_(x,z), k -> new ArrayList<>()).add(v);
        }
        boolean intersects(BoundingBox b) {
            for (Volume station : stations) if (station.intersects(b)) return true;
            for (int x = b.m_162395_() >> 4; x <= b.m_162399_() >> 4; x++)
                for (int z = b.m_162398_() >> 4; z <= b.m_162401_() >> 4; z++) {
                    List<Volume> volumes = chunks.get(ChunkPos.m_45589_(x,z));
                    if (volumes != null) for (Volume v : volumes) if (v.intersects(b)) return true;
                }
            return false;
        }
    }
}
