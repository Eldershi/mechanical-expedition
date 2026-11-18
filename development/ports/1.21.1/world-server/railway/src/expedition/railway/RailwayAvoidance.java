package expedition.railway;

import com.hxzhitang.tongdarailway.railway.RailwayBuilder;
import com.hxzhitang.tongdarailway.railway.RailwayMap;
import com.hxzhitang.tongdarailway.railway.RegionPos;
import com.hxzhitang.tongdarailway.structure.ModStructureManager;
import com.hxzhitang.tongdarailway.structure.RailwayTemplate;
import com.hxzhitang.tongdarailway.util.CurveRoute;
import java.util.Collections;
import java.util.Map;
import java.util.Set;
import java.util.WeakHashMap;
import net.minecraft.server.level.GenerationChunkHolder;
import net.minecraft.server.level.WorldGenRegion;
import net.minecraft.util.StaticCache2D;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.chunk.status.ChunkStep;
import net.minecraft.world.level.chunk.status.WorldGenContext;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.phys.Vec3;

public final class RailwayAvoidance {
    // A station can straddle a TongDa planning region. The largest native station is 79 blocks wide.
    private static final int STATION_REGION_PADDING = 64;
    private static final ThreadLocal<WorldGenRegion> GENERATION = new ThreadLocal<>();
    private static final Map<ChunkGenerator, Boolean> ENABLED = Collections.synchronizedMap(new WeakHashMap<>());

    private RailwayAvoidance() {}

    public static void duringStructureStarts(WorldGenContext context, ChunkStep step,
                                             StaticCache2D<GenerationChunkHolder> cache,
                                             ChunkAccess chunk, Runnable work) {
        if (!context.level().dimension().equals(Level.OVERWORLD)
                || !ENABLED.computeIfAbsent(context.generator(), RailwayAvoidance::hasRailwayFeature)) {
            work.run();
            return;
        }
        GENERATION.set(new WorldGenRegion(context.level(), cache, step, chunk));
        try {
            work.run();
        } finally {
            GENERATION.remove();
        }
    }

    private static boolean hasRailwayFeature(ChunkGenerator generator) {
        return generator.getBiomeSource().possibleBiomes().stream().anyMatch(biome ->
            generator.getBiomeGenerationSettings(biome).features().stream().anyMatch(step ->
                step.stream().anyMatch(feature -> feature.unwrapKey().stream().anyMatch(key ->
                    key.location().toString().equals("tongdarailway:railway_and_station")))));
    }

    public static boolean testsFullStructure() {
        return GENERATION.get() != null;
    }

    public static boolean conflicts(StructureStart structure, long seed) {
        WorldGenRegion context = GENERATION.get();
        if (context == null || !structure.isValid()) {
            return false;
        }
        var builder = RailwayBuilder.getInstance(seed, context);
        var box = structure.getBoundingBox();
        var first = RegionPos.regionPosFromWorldPos(box.minX() - STATION_REGION_PADDING, box.minZ() - STATION_REGION_PADDING);
        var last = RegionPos.regionPosFromWorldPos(box.maxX() + STATION_REGION_PADDING, box.maxZ() + STATION_REGION_PADDING);
        for (int x = first.x(); x <= last.x(); x++) {
            for (int z = first.z(); z <= last.z(); z++) {
                var region = new RegionPos(x, z);
                builder.generateRailway(region);
                var plan = builder.regionRailways.get(region);
                if (plan != null && structure.getPieces().stream().anyMatch(piece -> overlaps(plan, piece.getBoundingBox()))) {
                    return true;
                }
            }
        }
        return false;
    }

    public static boolean overlaps(RailwayMap plan, BoundingBox piece) {
        for (var station : plan.stations) {
            if (station.stationTemplate() != null
                    && station.stationTemplate().getBeardifierBox(station.placePos()).inflatedBy(2).intersects(piece)) {
                return true;
            }
        }
        for (int x = piece.minX() >> 4; x <= piece.maxX() >> 4; x++) {
            for (int z = piece.minZ() >> 4; z <= piece.maxZ() >> 4; z++) {
                var chunk = new ChunkPos(x, z);
                for (var route : plan.routeMap.getOrDefault(chunk, Set.of())) {
                    if (intersectsRoute(route, chunk, piece)) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    private static boolean intersectsRoute(CurveRoute route, ChunkPos chunk, BoundingBox piece) {
        int templateSeed = route.getSegments().size();
        RailwayTemplate[] templates = {ModStructureManager.getRandomGround(templateSeed),
            ModStructureManager.getRandomBridge(templateSeed), ModStructureManager.getRandomTunnel(templateSeed)};
        double radius = 4;
        double low = -3;
        double high = 3;
        for (var template : templates) {
            if (template != null) {
                radius = Math.max(radius, template.getDepth() / 2.0 + 3);
                low = Math.min(low, template.getLowerBound() - 3);
                high = Math.max(high, template.getUpperBound() + 3);
            }
        }
        for (int x = Math.max(piece.minX(), chunk.getMinBlockX()); x <= Math.min(piece.maxX(), chunk.getMaxBlockX()); x++) {
            for (int z = Math.max(piece.minZ(), chunk.getMinBlockZ()); z <= Math.min(piece.maxZ(), chunk.getMaxBlockZ()); z++) {
                Vec3 point = route.getFrame(new Vec3(x, 80, z)).nearestPoint;
                if (Math.hypot(point.x - x, point.z - z) <= radius
                        && point.y + high >= piece.minY() && point.y + low <= piece.maxY()) {
                    return true;
                }
            }
        }
        return false;
    }
}
