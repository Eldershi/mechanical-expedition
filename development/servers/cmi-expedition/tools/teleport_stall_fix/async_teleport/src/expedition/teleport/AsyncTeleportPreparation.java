package expedition.teleport;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.arguments.coordinates.Coordinates;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.commands.TeleportCommand;
import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.ChunkStatus;
import net.minecraft.world.phys.Vec3;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Preload cold command destinations without executing a blocking chunk task on the tick thread. */
public final class AsyncTeleportPreparation {
    private static final Logger LOG = LoggerFactory.getLogger("ExpeditionAsyncTeleport");
    private static final AtomicLong IDS = new AtomicLong();
    private static final AtomicLong QUEUED = new AtomicLong();
    private static final AtomicLong COMPLETED = new AtomicLong();
    private static final AtomicLong FAILED = new AtomicLong();
    private static final Map<UUID, Long> LATEST = new ConcurrentHashMap<>();
    private static final Map<Long, Pending> PENDING = new ConcurrentHashMap<>();
    private static final ThreadLocal<Boolean> RESUMING = ThreadLocal.withInitial(() -> false);
    private static final TicketType<Long> PREPARATION = TicketType.m_9462_(
        "expedition_teleport_preparation", Long::compare);
    private static final java.util.concurrent.ExecutorService REQUESTS = Executors.newSingleThreadExecutor(
        new ThreadFactory() {
            public Thread newThread(Runnable r) {
                Thread t = new Thread(r, "Expedition-Chunk-Requests");
                t.setDaemon(true);
                return t;
            }
        });
    private static volatile Method positions;
    private AsyncTeleportPreparation() {}

    public static long getQueued() { return QUEUED.get(); }
    public static long getCompleted() { return COMPLETED.get(); }
    public static long getFailed() { return FAILED.get(); }

    public static void cancelFor(Collection<? extends Entity> targets) {
        java.util.Set<Long> oldIds = new java.util.HashSet<>();
        for (Entity entity : targets) {
            Long old = LATEST.remove(entity.m_20148_());
            if (old != null) oldIds.add(old);
        }
        for (Long old : oldIds) {
            Pending pending = PENDING.get(old);
            if (pending != null && !pending.hasCurrentTargets()) pending.close();
        }
    }

    private static final class Pending {
        final long id;
        final ServerChunkCache chunks;
        final List<ChunkPos> required;
        final List<UUID> targets;
        final AtomicBoolean closed = new AtomicBoolean();
        volatile CompletableFuture<Void> future;
        Pending(long id, ServerChunkCache chunks, List<ChunkPos> required, List<Entity> targets) {
            this.id = id; this.chunks = chunks; this.required = required;
            this.targets = targets.stream().map(Entity::m_20148_).toList();
        }
        // Called only on the server thread, including cancellation/supersession.
        void close() {
            if (!closed.compareAndSet(false, true)) return;
            PENDING.remove(id, this);
            for (ChunkPos chunk : required) chunks.m_8438_(PREPARATION, chunk, 0, id);
            for (UUID target : targets) LATEST.remove(target, id);
            CompletableFuture<Void> active = future;
            if (active != null && !active.isDone()) active.cancel(false);
        }
        boolean hasCurrentTargets() {
            return targets.stream().anyMatch(target -> Long.valueOf(id).equals(LATEST.get(target)));
        }
    }

    /** Called only after Brigadier has validated the command and selected its targets. */
    public static boolean defer(CommandSourceStack source, Collection<? extends Entity> targets,
            ServerLevel destination, Coordinates coordinates, Coordinates rotation, Object facing) {
        if (RESUMING.get()) {
            // Consume this one re-entry. Nested teleport commands issued by a
            // Forge event must still take the normal preparation path.
            RESUMING.set(false);
            return false;
        }
        Vec3 position = coordinates.m_6955_(source);
        if (!Double.isFinite(position.f_82479_) || !Double.isFinite(position.f_82480_)
                || !Double.isFinite(position.f_82481_)
                || !Level.m_46741_(BlockPos.m_274561_(position.f_82479_, position.f_82480_, position.f_82481_))) {
            return false; // Keep vanilla's bounds/error handling.
        }
        List<Entity> selected = new ArrayList<>(targets);
        if (selected.isEmpty()) return false;
        long id = IDS.incrementAndGet();
        // A later warm teleport must supersede an earlier pending cold teleport too.
        java.util.Set<Long> previous = new java.util.HashSet<>();
        for (Entity entity : selected) {
            Long old = LATEST.put(entity.m_20148_(), id);
            if (old != null) previous.add(old);
        }
        for (Long old : previous) {
            Pending pending = PENDING.get(old);
            if (pending != null && !pending.hasCurrentTargets()) pending.close();
        }
        int centerX = ((int) Math.floor(position.f_82479_)) >> 4;
        int centerZ = ((int) Math.floor(position.f_82481_)) >> 4;
        ServerChunkCache chunks = destination.m_7726_();
        List<ChunkPos> required = new ArrayList<>(9);
        boolean ready = true;
        for (int x = centerX - 1; x <= centerX + 1; x++) {
            for (int z = centerZ - 1; z <= centerZ + 1; z++) {
                required.add(new ChunkPos(x, z));
                if (chunks.m_7131_(x, z) == null) ready = false;
            }
        }
        if (ready) {
            for (Entity entity : selected) LATEST.remove(entity.m_20148_(), id);
            return false;
        }
        MinecraftServer server = source.m_81377_();
        // UNKNOWN tickets created by getChunkFuture expire after one tick. These
        // unique tickets survive while the server keeps ticking and cannot be
        // removed by a different request for the same destination.
        for (ChunkPos chunk : required) chunks.m_8387_(PREPARATION, chunk, 0, id);
        Pending pending = new Pending(id, chunks, required, selected);
        PENDING.put(id, pending);
        Map<UUID, Level> origin = new java.util.HashMap<>();
        for (Entity entity : selected) origin.put(entity.m_20148_(), entity.m_9236_());
        QUEUED.incrementAndGet();
        long started = System.nanoTime();
        source.m_288197_(() -> Component.m_237113_("正在准备传送目的地，准备完成后自动传送。"), false);
        LOG.info("Preparing request {} for {} target(s), dimension={}, chunk={},{}", id,
            selected.size(), destination.m_46472_().m_135782_(), centerX, centerZ);

        // It is essential to call getChunkFuture OFF the tick thread: its main
        // thread branch performs managedBlock even though it returns a Future.
        CompletableFuture<Void> preparation = CompletableFuture.supplyAsync(() -> {
            List<CompletableFuture<?>> futures = new ArrayList<>(required.size());
            for (ChunkPos chunk : required) {
                if (pending.closed.get()) throw new java.util.concurrent.CancellationException("Superseded teleport");
                futures.add(chunks.m_8431_(chunk.f_45578_, chunk.f_45579_, ChunkStatus.f_62326_, true)
                    .thenApply(result -> result.map(access -> access, failure -> {
                        throw new IllegalStateException("Destination chunk unavailable: " + failure);
                    })));
            }
            return CompletableFuture.allOf(futures.toArray(CompletableFuture[]::new));
        }, REQUESTS).thenCompose(future -> future);
        pending.future = preparation;
        preparation.orTimeout(300, TimeUnit.SECONDS).whenComplete((nothing, failure) -> server.execute(() -> {
            if (pending.closed.get()) return;
            try {
                if (failure != null) {
                    FAILED.incrementAndGet();
                    LOG.warn("Teleport preparation {} failed", id, failure);
                    source.m_81352_(Component.m_237113_("传送目的地未能准备完成，本次传送已取消。"));
                    return;
                }
                List<Entity> current = new ArrayList<>();
                for (Entity entity : selected) {
                    if (Long.valueOf(id).equals(LATEST.get(entity.m_20148_()))
                            && !entity.m_213877_() && entity.m_6084_()
                            && entity.m_9236_() == origin.get(entity.m_20148_())) current.add(entity);
                }
                if (current.isEmpty()) return;
                // Re-enter vanilla only when the destination is already FULL.
                // All Forge teleport events, rotations, facing, and feedback
                // remain in the original command implementation.
                invokePositions(source, current, destination, coordinates, rotation, facing);
                COMPLETED.incrementAndGet();
                LOG.info("Completed request {} after {} ms", id,
                    TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - started));
            } catch (Throwable error) {
                FAILED.incrementAndGet();
                LOG.warn("Teleport completion {} failed", id, error);
                source.m_81352_(error instanceof CommandSyntaxException syntax
                    ? syntax.getRawMessage() instanceof Component c ? c : Component.m_237113_(syntax.getMessage())
                    : Component.m_237113_("传送失败，请重新尝试。"));
            } finally {
                pending.close();
            }
        }));
        return true;
    }

    private static void invokePositions(CommandSourceStack source, Collection<? extends Entity> targets,
            ServerLevel destination, Coordinates coordinates, Coordinates rotation, Object facing) throws Throwable {
        Method method = positions;
        if (method == null) {
            method = TeleportCommand.class.getDeclaredMethod("m_139025_", CommandSourceStack.class,
                Collection.class, ServerLevel.class, Coordinates.class, Coordinates.class,
                Class.forName("net.minecraft.server.commands.TeleportCommand$LookAt"));
            method.setAccessible(true);
            positions = method;
        }
        RESUMING.set(true);
        try { method.invoke(null, source, targets, destination, coordinates, rotation, facing); }
        catch (InvocationTargetException error) { throw error.getCause(); }
        finally { RESUMING.remove(); }
    }
}
