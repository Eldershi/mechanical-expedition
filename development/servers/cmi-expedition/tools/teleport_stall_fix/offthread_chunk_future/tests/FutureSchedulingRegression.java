import com.mojang.datafixers.util.Either;
import expedition.chunkfuture.ChunkFutureAwaiter;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionException;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicReference;

/** Regression for the actual scheduling failure, independent of world content. */
public final class FutureSchedulingRegression {
    public static void main(String[] args) throws Exception {
        preservesServerProgressWhileLocatorWaits();
        demonstratesOldPatternBlocksServerProgress();
        mandatoryMissingFails();
        exceptionalGenerationPropagates();
        retainsTicketWhileServerTicks();
        releasesTicketAfterFailure();
        System.out.println("PASS: external wait preserves main-thread progress and result/error contracts");
    }

    private static void preservesServerProgressWhileLocatorWaits() throws Exception {
        ExecutorService server = Executors.newSingleThreadExecutor();
        ExecutorService locator = Executors.newSingleThreadExecutor();
        CompletableFuture<Either<String, String>> generation = new CompletableFuture<>();
        CountDownLatch requestScheduled = new CountDownLatch(1);
        try {
            CompletableFuture<String> result = CompletableFuture.supplyAsync(() -> {
                // The real Minecraft getChunkFuture external branch schedules only
                // future acquisition, then flattens; it never waits in this task.
                CompletableFuture<Either<String, String>> requested =
                        CompletableFuture.supplyAsync(() -> {
                            requestScheduled.countDown();
                            return generation;
                        }, server).thenCompose(f -> f);
                return ChunkFutureAwaiter.awaitMandatory(requested);
            }, locator);
            require(requestScheduled.await(2, TimeUnit.SECONDS), "request never scheduled");
            require(CompletableFuture.supplyAsync(() -> "tick", server)
                    .get(2, TimeUnit.SECONDS).equals("tick"), "server cannot tick");
            require(!result.isDone(), "locator finished before generation");
            generation.complete(Either.left("same-authoritative-chunk"));
            require(result.get(2, TimeUnit.SECONDS).equals("same-authoritative-chunk"),
                    "chunk identity/result changed");
        } finally {
            generation.complete(Either.right("cleanup"));
            server.shutdownNow();
            locator.shutdownNow();
        }
    }

    private static void demonstratesOldPatternBlocksServerProgress() throws Exception {
        ExecutorService server = Executors.newSingleThreadExecutor();
        CompletableFuture<String> generation = new CompletableFuture<>();
        CountDownLatch requestStarted = new CountDownLatch(1);
        try {
            CompletableFuture<String> oldRequest = CompletableFuture.supplyAsync(() -> {
                requestStarted.countDown();
                return generation.join();
            }, server);
            require(requestStarted.await(2, TimeUnit.SECONDS), "old request never started");
            CompletableFuture<String> heartbeat = CompletableFuture.supplyAsync(() -> "tick", server);
            try {
                heartbeat.get(100, TimeUnit.MILLISECONDS);
                throw new AssertionError("old blocking request unexpectedly let server tick");
            } catch (TimeoutException expected) {
                require(!oldRequest.isDone(), "old request finished early");
            }
            generation.complete("chunk");
            require(oldRequest.get(2, TimeUnit.SECONDS).equals("chunk"), "old result missing");
            require(heartbeat.get(2, TimeUnit.SECONDS).equals("tick"), "old server did not recover");
        } finally {
            generation.complete("cleanup");
            server.shutdownNow();
        }
    }

    private static void mandatoryMissingFails() {
        try {
            ChunkFutureAwaiter.awaitMandatory(
                    CompletableFuture.completedFuture(Either.<String, String>right("unloaded")));
            throw new AssertionError("mandatory missing chunk silently returned");
        } catch (IllegalStateException expected) {
            require(expected.getMessage().contains("unloaded"), "missing reason was lost");
        }
    }

    private static void exceptionalGenerationPropagates() {
        RuntimeException cause = new RuntimeException("generation failed");
        CompletableFuture<Either<String, String>> future = new CompletableFuture<>();
        future.completeExceptionally(cause);
        try {
            ChunkFutureAwaiter.awaitMandatory(future);
            throw new AssertionError("exceptional generation silently returned");
        } catch (CompletionException expected) {
            require(expected.getCause() == cause, "generation cause changed");
        }
    }

    private static void retainsTicketWhileServerTicks() throws Exception {
        ExecutorService server = Executors.newSingleThreadExecutor();
        ExecutorService locator = Executors.newSingleThreadExecutor();
        AtomicBoolean held = new AtomicBoolean();
        AtomicReference<Thread> serverThread = new AtomicReference<>();
        CountDownLatch requested = new CountDownLatch(1);
        CountDownLatch released = new CountDownLatch(1);
        CompletableFuture<Either<String, String>> generation = new CompletableFuture<>();
        try {
            CompletableFuture<String> result = CompletableFuture.supplyAsync(() ->
                    ChunkFutureAwaiter.awaitWithTicket(
                            () -> CompletableFuture.runAsync(() -> {
                                serverThread.set(Thread.currentThread());
                                held.set(true);
                            }, server),
                            () -> {
                                require(Thread.currentThread() != serverThread.get(),
                                        "future requested on server thread");
                                require(held.get(), "ticket not acquired before request");
                                requested.countDown();
                                return generation;
                            },
                            () -> server.execute(() -> {
                                held.set(false);
                                released.countDown();
                            })), locator);
            require(requested.await(2, TimeUnit.SECONDS), "request never reached");
            for (int i = 0; i < 5; i++) {
                require(CompletableFuture.supplyAsync(held::get, server)
                        .get(2, TimeUnit.SECONDS), "ticket removed while generation pending");
            }
            require(!result.isDone(), "pending generation completed early");
            generation.complete(Either.left("ticketed-chunk"));
            require(result.get(2, TimeUnit.SECONDS).equals("ticketed-chunk"), "wrong result");
            require(released.await(2, TimeUnit.SECONDS), "completed request leaked ticket");
            require(!held.get(), "ticket remained after release");
        } finally {
            generation.complete(Either.right("cleanup"));
            locator.shutdownNow();
            server.shutdownNow();
        }
    }

    private static void releasesTicketAfterFailure() {
        AtomicBoolean released = new AtomicBoolean();
        CompletableFuture<Either<String, String>> failed = new CompletableFuture<>();
        failed.completeExceptionally(new IllegalArgumentException("test failure"));
        try {
            ChunkFutureAwaiter.awaitWithTicket(
                    () -> CompletableFuture.completedFuture(null),
                    () -> failed, () -> released.set(true));
            throw new AssertionError("failed request unexpectedly succeeded");
        } catch (CompletionException expected) {
            require(released.get(), "failed request leaked ticket");
        }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
}
