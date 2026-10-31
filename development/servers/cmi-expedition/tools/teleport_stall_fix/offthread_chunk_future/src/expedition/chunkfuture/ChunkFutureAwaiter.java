package expedition.chunkfuture;

import com.mojang.datafixers.util.Either;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.atomic.AtomicLong;
import java.util.function.Supplier;

/** Waits on the external caller, after the server has only scheduled generation. */
public final class ChunkFutureAwaiter {
    private static final AtomicLong REQUESTS = new AtomicLong();

    private ChunkFutureAwaiter() {}

    public static long getBridgedRequests() {
        return REQUESTS.get();
    }

    public static <T, F> T awaitMandatory(CompletableFuture<Either<T, F>> future) {
        REQUESTS.incrementAndGet();
        return future.join().map(chunk -> chunk, failure -> {
            throw new IllegalStateException("Chunk not there when requested: " + failure);
        });
    }

    /** Acquire on main, resume this external caller, and always release on main. */
    public static <T, F> T awaitWithTicket(
            Supplier<CompletableFuture<Void>> acquire,
            Supplier<CompletableFuture<Either<T, F>>> request,
            Runnable release) {
        try {
            acquire.get().join();
            // Deliberately execute this supplier on the original external caller.
            // A thenCompose continuation could execute on main and block it again.
            return awaitMandatory(request.get());
        } finally {
            release.run();
        }
    }
}
