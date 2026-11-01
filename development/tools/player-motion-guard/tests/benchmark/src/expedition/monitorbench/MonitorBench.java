package expedition.monitorbench;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.mojang.authlib.GameProfile;
import java.lang.management.GarbageCollectorMXBean;
import java.lang.management.ManagementFactory;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.locks.LockSupport;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.network.Connection;
import net.minecraft.network.PacketSendListener;
import net.minecraft.network.protocol.Packet;
import net.minecraft.network.protocol.PacketFlow;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.ServerGamePacketListenerImpl;
import net.minecraft.server.players.PlayerList;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.GameType;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.registries.ForgeRegistries;

/** Test-only workload, driven by actual Forge server ticks and player physics. */
@Mod("expedition_monitor_bench")
public final class MonitorBench {
    private static final Gson JSON = new GsonBuilder().serializeSpecialFloatingPointValues().create();
    private final int players = Math.max(10, Integer.getInteger("monitorbench.players", 10));
    private final int rounds = Math.max(1, Integer.getInteger("monitorbench.rounds", 3));
    private final int warmupTicks = Math.max(40, Integer.getInteger("monitorbench.warmupTicks", 200));
    private final int measuredTicks = Math.max(100, Integer.getInteger("monitorbench.measuredTicks", 400));
    private final int stallMillis = Math.max(0, Integer.getInteger("monitorbench.stallMillis", 150));
    private final int itemNbtBytes = Math.max(0, Integer.getInteger("monitorbench.itemNbtBytes", 1024));
    private final String mode = System.getProperty("monitorbench.mode", "unspecified");
    private final String[] scenarios = System.getProperty("monitorbench.scenarios", "steady,incident").split(",");
    private final List<ServerPlayer> actors = new ArrayList<>();
    private final com.sun.management.ThreadMXBean threads =
            (com.sun.management.ThreadMXBean) ManagementFactory.getThreadMXBean();
    private final com.sun.management.OperatingSystemMXBean os =
            (com.sun.management.OperatingSystemMXBean) ManagementFactory.getOperatingSystemMXBean();
    private final List<GarbageCollectorMXBean> collectors = ManagementFactory.getGarbageCollectorMXBeans();
    private final long[] wallNs = new long[measuredTicks];
    private final long[] mainCpuNs = new long[measuredTicks];
    private final long[] mainAllocatedBytes = new long[measuredTicks];
    private MinecraftServer server;
    private ServerLevel level;
    private Item sword, pickaxe, stone;
    private int tick, window, warmup, sample;
    private boolean ready, measuring, complete, tailRegistered;
    private long startNs, startCpu, startAllocation, playerStarts, playerEnds;
    private long teleports, equipmentChanges, unsafeAttempts, blockPairs;
    private Counters before;
    private Map<String, Object> diagnosticsBefore;

    public MonitorBench() {
        MinecraftForge.EVENT_BUS.register(this);
        if (threads.isThreadCpuTimeSupported() && !threads.isThreadCpuTimeEnabled())
            threads.setThreadCpuTimeEnabled(true);
        if (threads.isThreadAllocatedMemorySupported() && !threads.isThreadAllocatedMemoryEnabled())
            threads.setThreadAllocatedMemoryEnabled(true);
        for (String scenario : scenarios)
            if (!scenario.equals("steady") && !scenario.equals("incident"))
                throw new IllegalArgumentException("Unsupported workload: " + scenario);
    }

    @SubscribeEvent
    public void started(ServerStartedEvent event) {
        try {
            server = event.getServer();
            level = server.m_129783_();
            sword = ForgeRegistries.ITEMS.getValue(new ResourceLocation("minecraft:iron_sword"));
            pickaxe = ForgeRegistries.ITEMS.getValue(new ResourceLocation("minecraft:diamond_pickaxe"));
            stone = ForgeRegistries.ITEMS.getValue(new ResourceLocation("minecraft:stone"));
            if (sword == null || pickaxe == null || stone == null) throw new AssertionError("Vanilla item registry unavailable");
            // Warm the entire arena before recording any timings.
            for (int x = -2; x <= (players * 8 + 32) / 16; x++)
                for (int z = -2; z <= 3; z++) level.m_6325_(x, z);
            // Modern flat layers begin at the dimension minimum, not Y=0.
            // Build an explicit warmed arena at the fixture's Y=3 support plane.
            for (int x = -16; x <= players * 8 + 24; x++)
                for (int z = 8; z <= 40; z++)
                    level.m_46597_(new BlockPos(x, 3, z), Blocks.f_50069_.m_49966_());
            server.m_129892_().m_230957_(server.m_129893_(), "gamerule doMobSpawning false");
            server.m_129892_().m_230957_(server.m_129893_(), "gamerule randomTickSpeed 0");
            for (int i = 0; i < players; i++) {
                UUID id = new UUID(0x5b7b000000000000L, i + 1L);
                ServerPlayer player = new ServerPlayer(server, level, new GameProfile(id, "Bench" + i));
                // Ordinary ServerPlayer avoids FakePlayer exclusions in audit mods.
                // Keep the real teleport implementation; discard only outgoing packets.
                player.f_8906_ = new NoNetworkHandler(server, player);
                player.f_8941_.m_143473_(GameType.CREATIVE);
                player.m_6034_(anchorX(i), 4.0, 16.5);
                level.m_8845_(player);
                registerInPlayerList(player);
                actors.add(player);
                notifyArchitecturyJoin(player);
            }
            if (server.m_6846_().m_11314_().size() < players)
                throw new AssertionError("Actors absent from real server player list");
            warmup = warmupTicks;
            ready = true;
            System.out.println("MONITOR_BENCH_READY players=" + players
                    + " physics=ServerPlayer.doTick-in-real-ServerTickEvent mode=" + mode);
        } catch (Throwable failure) { fail(failure); }
    }

    private static double anchorX(int index) { return index * 8.0 + 0.5; }

    @SuppressWarnings("unchecked")
    private void registerInPlayerList(ServerPlayer player) throws ReflectiveOperationException {
        // Forge exposes an unmodifiable public view. Modify only this disposable
        // fixture's backing collection and UUID index, never an installed server.
        var listField = PlayerList.class.getDeclaredField("f_11196_");
        var mapField = PlayerList.class.getDeclaredField("f_11197_");
        listField.setAccessible(true);
        mapField.setAccessible(true);
        ((List<ServerPlayer>) listField.get(server.m_6846_())).add(player);
        ((Map<UUID, ServerPlayer>) mapField.get(server.m_6846_())).put(player.m_20148_(), player);
    }
    private String scenario() { return scenarios[window % scenarios.length]; }
    private int round() { return window / scenarios.length; }
    private String windowId() { return "r" + round() + "-" + scenario(); }

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public void beforeTick(TickEvent.ServerTickEvent event) {
        if (!ready || complete || event.phase != TickEvent.Phase.START) return;
        startNs = System.nanoTime();
        startCpu = threads.getCurrentThreadCpuTime();
        startAllocation = allocation(Thread.currentThread().getId());
    }

    @SubscribeEvent(priority = EventPriority.NORMAL)
    public void workload(TickEvent.ServerTickEvent event) {
        if (!ready || complete || event.phase != TickEvent.Phase.START) return;
        try {
            if (!tailRegistered) {
                // Register the END observer after startup-installed recorder listeners.
                // This includes their END work even when they also use LOWEST priority.
                MinecraftForge.EVENT_BUS.register(new TailObserver());
                tailRegistered = true;
            }
            tick++;
            boolean incident = scenario().equals("incident");
            int local = measuring ? sample : -warmup;
            for (int i = 0; i < actors.size(); i++) {
                ServerPlayer player = actors.get(i);
                if (tick % (incident ? 20 : 100) == i % (incident ? 20 : 100)) {
                    player.m_8999_(level, anchorX(i), 4.0, 16.5 + ((tick / 100) % 2) * 8,
                            0.0f, 0.0f);
                    if (measuring) teleports++;
                }
                if (tick % 20 == 0) {
                    ItemStack item = new ItemStack((tick / 20) % 2 == 0 ? sword : pickaxe);
                    item.m_41784_().m_128359_("monitor_benchmark", "x".repeat(itemNbtBytes));
                    player.m_8061_(EquipmentSlot.MAINHAND, item);
                    if (measuring) equipmentChanges++;
                }
                if (tick % 20 == i % 20) {
                    placeBreak(player, i);
                    if (measuring) blockPairs++;
                }
                double dx = (tick / 40) % 2 == 0 ? 0.08 : -0.08;
                player.m_20256_(new Vec3(dx, -0.08, 0.02));
                // A real ServerPlayer physics tick, including Forge PlayerTick events.
                player.m_9240_();
            }
            if (measuring && incident && sample % 80 == 40) {
                ServerPlayer player = actors.get((sample / 80) % actors.size());
                player.m_20256_(new Vec3(Double.NaN, 0, 0));
                if (player.m_20184_().m_82556_() != 0)
                    throw new AssertionError("Unsafe setter was not rejected");
                unsafeAttempts++;
            }
            if (measuring && incident && local == measuredTicks / 2 && stallMillis > 0)
                LockSupport.parkNanos(stallMillis * 1_000_000L);
        } catch (Throwable failure) { fail(failure); }
    }

    public void afterTick(TickEvent.ServerTickEvent event) {
        if (!ready || complete || event.phase != TickEvent.Phase.END) return;
        try {
            long elapsed = System.nanoTime() - startNs;
            long cpu = threads.getCurrentThreadCpuTime() - startCpu;
            long allocated = difference(allocation(Thread.currentThread().getId()), startAllocation);
            if (!measuring) {
                if (--warmup <= 0) beginWindow();
                return;
            }
            wallNs[sample] = elapsed;
            mainCpuNs[sample] = Math.max(0, cpu);
            mainAllocatedBytes[sample] = allocated;
            if (++sample == measuredTicks) finishWindow();
        } catch (Throwable failure) { fail(failure); }
    }

    @SubscribeEvent
    public void playerTick(TickEvent.PlayerTickEvent event) {
        if (!ready || !measuring || complete || !actors.contains(event.player)) return;
        if (event.phase == TickEvent.Phase.START) playerStarts++;
        else playerEnds++;
    }

    private void beginWindow() {
        sample = 0;
        playerStarts = playerEnds = teleports = equipmentChanges = unsafeAttempts = blockPairs = 0;
        diagnosticsBefore = diagnosticsStatus();
        before = counters();
        measuring = true;
        System.out.println("MONITOR_BENCH_BEGIN " + windowId());
    }

    private void finishWindow() {
        Counters after = counters();
        long expected = (long) players * measuredTicks;
        if (playerStarts < expected || playerEnds < expected)
            throw new AssertionError("Real PlayerTick callbacks missing: " + playerStarts + "/" + playerEnds
                    + " expected >= " + expected);
        Map<String, Object> diagnosticsAfter = diagnosticsStatus();
        if (mode.equals("monitor")) {
            if (!Boolean.TRUE.equals(diagnosticsAfter.get("enabled"))
                    || number(diagnosticsAfter, "trackedPlayers") < players
                    || number(diagnosticsAfter, "totalSnapshots") - number(diagnosticsBefore, "totalSnapshots") < expected
                    || number(diagnosticsAfter, "equipmentChanges") <= number(diagnosticsBefore, "equipmentChanges")
                    || number(diagnosticsAfter, "eventCount") <= number(diagnosticsBefore, "eventCount"))
                throw new AssertionError("Monitoring did not observe the actual ten-player workload: " + diagnosticsAfter);
            Object writerAfter = diagnosticsAfter.get("writer"), writerBefore = diagnosticsBefore.get("writer");
            if (!(writerAfter instanceof Map<?, ?> wa) || !(writerBefore instanceof Map<?, ?> wb)
                    || number(wa, "lastWrittenSequence") <= number(wb, "lastWrittenSequence"))
                throw new AssertionError("Monitoring produced no persisted events during the window");
        }
        Map<String, Object> report = new LinkedHashMap<>();
        report.put("window", windowId());
        report.put("mode", mode);
        report.put("round", round());
        report.put("scenario", scenario());
        report.put("players", players);
        report.put("ticks", measuredTicks);
        report.put("wallElapsedNs", after.wall - before.wall);
        report.put("tickWallNs", percentiles(wallNs));
        report.put("mainThreadCpuNs", percentiles(mainCpuNs));
        report.put("mainThreadAllocatedBytes", sum(mainAllocatedBytes));
        report.put("processCpuNs", difference(after.processCpu, before.processCpu));
        report.put("liveThreadCpuNsApproximate", positiveMapDifference(after.threadCpu, before.threadCpu));
        report.put("liveThreadAllocatedBytesApproximate", positiveMapDifference(after.allocated, before.allocated));
        report.put("gcCollections", difference(after.gcCount, before.gcCount));
        report.put("gcTimeMillis", difference(after.gcMillis, before.gcMillis));
        report.put("heapUsedBefore", before.heap);
        report.put("heapUsedAfter", after.heap);
        report.put("playerTickStarts", playerStarts);
        report.put("playerTickEnds", playerEnds);
        report.put("teleports", teleports);
        report.put("equipmentChanges", equipmentChanges);
        report.put("unsafeAttempts", unsafeAttempts);
        report.put("realBlockPlaceBreakPairs", blockPairs);
        report.put("diagnosticsStatusBefore", diagnosticsBefore);
        report.put("diagnosticsStatusAfter", diagnosticsAfter);
        report.put("injectedStallMillis", scenario().equals("incident") ? stallMillis : 0);
        System.out.println("MONITOR_BENCH_WINDOW " + JSON.toJson(report));
        measuring = false;
        if (++window == rounds * scenarios.length) {
            complete = true;
            System.out.println("MONITOR_BENCH_PASSED windows=" + window);
        } else warmup = warmupTicks;
    }

    private long allocation(long id) {
        return threads.isThreadAllocatedMemorySupported() ? threads.getThreadAllocatedBytes(id) : -1;
    }

    private void placeBreak(ServerPlayer player, int index) {
        int x = (int) Math.floor(anchorX(index)) + 3;
        int z = (int) Math.floor(player.m_20189_()) + 2;
        BlockPos support = new BlockPos(x, 3, z), target = new BlockPos(x, 4, z);
        player.m_21008_(InteractionHand.MAIN_HAND, new ItemStack(stone, 64));
        BlockHitResult hit = new BlockHitResult(new Vec3(x + .5, 4, z + .5), Direction.UP, support, false);
        Object result = player.f_8941_.m_7179_(player, level, player.m_21205_(), InteractionHand.MAIN_HAND, hit);
        if (level.m_8055_(target).m_60795_() || !player.f_8941_.m_9280_(target))
            throw new AssertionError("Real player block placement/break failed: target=" + target
                    + " support=" + level.m_8055_(support) + " result=" + result);
    }

    private static void notifyArchitecturyJoin(ServerPlayer player) throws Exception {
        try {
            Object event = Class.forName("dev.architectury.event.events.common.PlayerEvent").getField("PLAYER_JOIN").get(null);
            Object invoker = Class.forName("dev.architectury.event.Event").getMethod("invoker").invoke(event);
            Class.forName("dev.architectury.event.events.common.PlayerEvent$PlayerJoin")
                    .getMethod("join", ServerPlayer.class).invoke(invoker, player);
        } catch (ClassNotFoundException absentOptionalDependency) {
            // The fixture also supports preparing a minimal non-audit control runtime.
        }
    }

    private static long number(Map<?, ?> map, String name) {
        Object value = map.get(name);
        return value instanceof Number number ? number.longValue() : -1;
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> diagnosticsStatus() {
        try {
            Class<?> type = Class.forName("expedition.motionguard.diagnostics.DiagnosticsService");
            Object service = type.getMethod("get").invoke(null);
            if (service == null) return Map.of("enabled", false, "notStarted", true);
            return new LinkedHashMap<>((Map<String, Object>) type.getMethod("status").invoke(service));
        } catch (ClassNotFoundException oldGuard) {
            return Map.of("enabled", false, "notInstalled", true);
        } catch (ReflectiveOperationException failure) {
            throw new IllegalStateException("Diagnostics status contract unavailable", failure);
        }
    }

    private static final class NoNetworkHandler extends ServerGamePacketListenerImpl {
        NoNetworkHandler(MinecraftServer server, ServerPlayer player) {
            super(server, new Connection(PacketFlow.SERVERBOUND), player);
        }
        @Override public void m_9829_(Packet<?> packet) {}
        @Override public void m_243119_(Packet<?> packet, PacketSendListener listener) {}
    }

    public final class TailObserver {
        @SubscribeEvent(priority = EventPriority.LOWEST)
        public void onTick(TickEvent.ServerTickEvent event) { afterTick(event); }
    }

    private Counters counters() {
        Counters result = new Counters();
        result.wall = System.nanoTime();
        result.processCpu = os.getProcessCpuTime();
        result.heap = ManagementFactory.getMemoryMXBean().getHeapMemoryUsage().getUsed();
        for (GarbageCollectorMXBean collector : collectors) {
            result.gcCount += Math.max(0, collector.getCollectionCount());
            result.gcMillis += Math.max(0, collector.getCollectionTime());
        }
        for (long id : threads.getAllThreadIds()) {
            result.threadCpu.put(id, threads.getThreadCpuTime(id));
            result.allocated.put(id, allocation(id));
        }
        return result;
    }

    private static long difference(long after, long before) {
        return after < 0 || before < 0 ? -1 : Math.max(0, after - before);
    }

    private static long positiveMapDifference(Map<Long, Long> after, Map<Long, Long> before) {
        long total = 0;
        for (var row : after.entrySet())
            if (row.getValue() >= 0) total += Math.max(0, row.getValue() - Math.max(0, before.getOrDefault(row.getKey(), 0L)));
        return total;
    }

    private static long sum(long[] values) {
        long total = 0;
        for (long value : values) { if (value < 0) return -1; total += value; }
        return total;
    }

    private static Map<String, Long> percentiles(long[] values) {
        long[] sorted = values.clone();
        Arrays.sort(sorted);
        Map<String, Long> result = new LinkedHashMap<>();
        result.put("p50", sorted[(int) Math.ceil(sorted.length * .50) - 1]);
        result.put("p95", sorted[(int) Math.ceil(sorted.length * .95) - 1]);
        result.put("max", sorted[sorted.length - 1]);
        result.put("sum", sum(values));
        return result;
    }

    private void fail(Throwable failure) {
        complete = true;
        System.out.println("MONITOR_BENCH_FAILED");
        failure.printStackTrace();
    }

    private static final class Counters {
        long wall, processCpu, gcCount, gcMillis, heap;
        final Map<Long, Long> threadCpu = new HashMap<>(), allocated = new HashMap<>();
    }
}
