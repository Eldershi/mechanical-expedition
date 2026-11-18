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
import net.minecraft.world.level.chunk.status.ChunkStatus;
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
    private static final TicketType<Long> PREPARATION = TicketType.create(
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
            Long old = LATEST.remove(entity.getUUID());
            if (old != null) oldIds.add(old);
        }
        for (Long old : oldIds) {
            Pending pending = PENDING.get(old);
            if (pending != null && !pending.hasCurrentTargets()) pending.close();
        }
    }

    public static void stop(MinecraftServer server) {
        for (Pending pending : PENDING.values()) {
            if (pending.server == server) pending.close();
        }
    }

    private static final class Pending {
        final long id;
        final MinecraftServer server;
        final ServerChunkCache chunks;
        final List<ChunkPos> required;
        final List<UUID> targets;
        final AtomicBoolean closed = new AtomicBoolean();
        volatile CompletableFuture<Void> future;
        Pending(long id, MinecraftServer server, ServerChunkCache chunks, List<ChunkPos> required, List<Entity> targets) {
            this.id = id; this.server = server; this.chunks = chunks; this.required = required;
            this.targets = targets.stream().map(Entity::getUUID).toList();
        }
        // Called only on the server thread, including cancellation/supersession.
        void close() {
            if (!closed.compareAndSet(false, true)) return;
            PENDING.remove(id, this);
            for (ChunkPos chunk : required) chunks.removeRegionTicket(PREPARATION, chunk, 0, id);
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
        Vec3 position = coordinates.getPosition(source);
        if (!Double.isFinite(position.x) || !Double.isFinite(position.y)
                || !Double.isFinite(position.z)
                || !Level.isInSpawnableBounds(BlockPos.containing(position.x, position.y, position.z))) {
            return false; // Keep vanilla's bounds/error handling.
        }
        List<Entity> selected = new ArrayList<>(targets);
        if (selected.isEmpty()) return false;
        long id = IDS.incrementAndGet();
        // A later warm teleport must supersede an earlier pending cold teleport too.
        java.util.Set<Long> previous = new java.util.HashSet<>();
        for (Entity entity : selected) {
            Long old = LATEST.put(entity.getUUID(), id);
            if (old != null) previous.add(old);
        }
        for (Long old : previous) {
            Pending pending = PENDING.get(old);
            if (pending != null && !pending.hasCurrentTargets()) pending.close();
        }
        int centerX = ((int) Math.floor(position.x)) >> 4;
        int centerZ = ((int) Math.floor(position.z)) >> 4;
        ServerChunkCache chunks = destination.getChunkSource();
        List<ChunkPos> required = new ArrayList<>(9);
        boolean ready = true;
        for (int x = centerX - 1; x <= centerX + 1; x++) {
            for (int z = centerZ - 1; z <= centerZ + 1; z++) {
                required.add(new ChunkPos(x, z));
                if (chunks.getChunkNow(x, z) == null) ready = false;
            }
        }
        if (ready) {
            for (Entity entity : selected) LATEST.remove(entity.getUUID(), id);
            return false;
        }
        MinecraftServer server = source.getServer();
        // UNKNOWN tickets created by getChunkFuture expire after one tick. These
        // unique tickets survive while the server keeps ticking and cannot be
        // removed by a different request for the same destination.
        for (ChunkPos chunk : required) chunks.addRegionTicket(PREPARATION, chunk, 0, id);
        Pending pending = new Pending(id, server, chunks, required, selected);
        PENDING.put(id, pending);
        Map<UUID, Level> origin = new java.util.HashMap<>();
        for (Entity entity : selected) origin.put(entity.getUUID(), entity.level());
        QUEUED.incrementAndGet();
        long started = System.nanoTime();
        source.sendSuccess(() -> Component.literal("正在准备传送目的地，准备完成后自动传送。"), false);
        LOG.info("Preparing request {} for {} target(s), dimension={}, chunk={},{}", id,
            selected.size(), destination.dimension().location(), centerX, centerZ);

        // It is essential to call getChunkFuture OFF the tick thread: its main
        // thread branch performs managedBlock even though it returns a Future.
        CompletableFuture<Void> preparation = CompletableFuture.supplyAsync(() -> {
            List<CompletableFuture<?>> futures = new ArrayList<>(required.size());
            for (ChunkPos chunk : required) {
                if (pending.closed.get()) throw new java.util.concurrent.CancellationException("Superseded teleport");
                futures.add(chunks.getChunkFuture(chunk.x, chunk.z, ChunkStatus.FULL, true)
                    .thenApply(result -> {
                        if (!result.isSuccess()) throw new IllegalStateException(
                            "Destination chunk unavailable: " + result.getError());
                        return result;
                    }));
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
                    source.sendFailure(Component.literal("传送目的地未能准备完成，本次传送已取消。"));
                    return;
                }
                List<Entity> current = new ArrayList<>();
                for (Entity entity : selected) {
                    if (Long.valueOf(id).equals(LATEST.get(entity.getUUID()))
                            && !entity.isRemoved() && entity.isAlive()
                            && entity.level() == origin.get(entity.getUUID())) current.add(entity);
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
                source.sendFailure(error instanceof CommandSyntaxException syntax
                    ? syntax.getRawMessage() instanceof Component c ? c : Component.literal(syntax.getMessage())
                    : Component.literal("传送失败，请重新尝试。"));
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
            method = TeleportCommand.class.getDeclaredMethod("teleportToPos", CommandSourceStack.class,
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
