package expedition.performance.policy;

import java.util.concurrent.atomic.LongAdder;
import java.util.concurrent.locks.LockSupport;

public final class ChunkQueuePolicy {
    public static volatile boolean enabled = true;
    public static final LongAdder requeued = new LongAdder(), dispatched = new LongAdder(), waits = new LongAdder();
    public static void backoff() {
        if (enabled && !Thread.currentThread().isInterrupted()) {
            waits.increment();
            LockSupport.parkNanos(250_000L); // Only failed dispatches; at most 0.25 ms requested wait.
        }
    }
    public static String stats() {
        return "{\"requeued\":"+requeued.sum()+",\"dispatched\":"+dispatched.sum()+",\"waits\":"+waits.sum()+"}";
    }

}
