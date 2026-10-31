package expedition.chunkfuture;

import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ChunkLevel;
import net.minecraft.server.level.DistanceManager;
import net.minecraft.server.level.ServerChunkCache;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.TicketType;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.chunk.ChunkAccess;
import net.minecraft.world.level.chunk.ChunkStatus;

/** Holds the exact requested generation status while the tick thread keeps running. */
public final class StructureChunkRequest {
    private static final TicketType<Long> REQUEST_TICKET =
            TicketType.m_9462_("expedition_structure_lookup", Long::compare);
    private static final AtomicLong NEXT_REQUEST = new AtomicLong();

    private StructureChunkRequest() {}

    public static ChunkAccess load(ServerChunkCache cache, ServerLevel level,
            DistanceManager distances, int x, int z, ChunkStatus status) {
        MinecraftServer server = level.m_7654_();
        ChunkPos pos = new ChunkPos(x, z);
        int ticketLevel = ChunkLevel.m_287141_(status);
        long requestId = NEXT_REQUEST.incrementAndGet();
        return ChunkFutureAwaiter.awaitWithTicket(
                () -> server.m_18707_(() ->
                        distances.m_140792_(REQUEST_TICKET, pos, ticketLevel, requestId)),
                () -> cache.m_8431_(x, z, status, true),
                () -> server.execute(() ->
                        distances.m_140823_(REQUEST_TICKET, pos, ticketLevel, requestId)));
    }
}
