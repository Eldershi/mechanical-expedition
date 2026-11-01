package expedition.motionguard.diagnostics;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.regex.Pattern;
import jdk.jfr.Configuration;
import jdk.jfr.FlightRecorder;
import jdk.jfr.Recording;
import jdk.jfr.RecordingState;

/** Bounded recording with independently forced snapshots in the server directory. */
public final class JfrRecorder implements AutoCloseable {
    private static final System.Logger LOG = System.getLogger("ExpeditionDiagnostics.JFR");
    private static final long RECORDING_BYTES = 256L * 1024 * 1024;
    private static final long ARCHIVE_BYTES = 768L * 1024 * 1024;
    private static final long MAX_SNAPSHOT_BYTES = RECORDING_BYTES + 32L * 1024 * 1024;
    private static final int ARCHIVE_FILES = 8;
    private static final long MIN_FREE_BYTES = 256L * 1024 * 1024;
    private final Path directory;
    private final String boot = UUID.randomUUID().toString().substring(0, 12);
    private final ScheduledThreadPoolExecutor worker;
    private final AtomicBoolean incidentPending = new AtomicBoolean();
    private final AtomicLong dropped = new AtomicLong();
    private final AtomicLong lastIncidentNanos = new AtomicLong();
    private volatile Recording recording;
    private volatile boolean started, closed, enabled;
    private volatile long dumps, lastDumpMillis, archiveBytes, archiveFiles, pruned, errors;
    private volatile String lastDump = "", error = "";
    private volatile boolean recoveredReceipt;

    public JfrRecorder(Path directory) {
        this.directory = directory;
        worker = new ScheduledThreadPoolExecutor(1, runnable -> {
            Thread thread = new Thread(runnable, "Expedition-Diagnostics-JFR");
            thread.setDaemon(true);
            return thread;
        });
        worker.setRemoveOnCancelPolicy(true);
        worker.setExecuteExistingDelayedTasksAfterShutdownPolicy(false);
        worker.setContinueExistingPeriodicTasksAfterShutdownPolicy(false);
    }

    /** Initialization and all recording I/O run on the single daemon worker. */
    public synchronized void start() {
        if (started || closed) return;
        started = true;
        if (!Boolean.parseBoolean(System.getProperty("expedition.diagnostics.jfr.enabled", "true"))) return;
        worker.execute(() -> {
            try {
                if (closed) return;
                if (!FlightRecorder.isAvailable()) throw new IOException("JFR unavailable in this runtime");
                Files.createDirectories(directory);
                recoverReceipt();
                prune();
                Recording candidate = new Recording(Configuration.getConfiguration("default"));
                recording = candidate;
                if (closed) { candidate.close(); recording = null; return; }
                candidate.setName("Expedition-Diagnostics-" + boot);
                candidate.setToDisk(true);
                candidate.setDumpOnExit(false);
                candidate.setMaxAge(Duration.ofMinutes(30));
                candidate.setMaxSize(RECORDING_BYTES);
                // 1.20.1 hooks use EventType.isEnabled(), including external recordings.
                candidate.enable("minecraft.ServerTickTime").withPeriod(Duration.ofSeconds(1));
                candidate.enable("minecraft.NetworkSummary").withPeriod(Duration.ofSeconds(1));
                candidate.enable("minecraft.ChunkGeneration").withThreshold(Duration.ofMillis(10));
                candidate.enable("minecraft.LoadWorld");
                // Packet payloads and individual per-packet events are not needed for this log.
                candidate.disable("minecraft.PacketReceived");
                candidate.disable("minecraft.PacketSent");
                candidate.start();
                if (closed) { candidate.close(); recording = null; return; }
                enabled = true;
                LOG.log(System.Logger.Level.INFO, "Continuous JFR enabled: 30 minutes / 256 MiB; durable snapshots under " + directory);
            } catch (Exception problem) {
                fail(problem);
                Recording current = recording;
                if (current != null) current.close();
                recording = null;
            }
        });
        worker.scheduleWithFixedDelay(() -> dump("periodic"), 5, 60, TimeUnit.SECONDS);
    }

    /** At most one queued incident, rate limited independently of the main tick. */
    public boolean requestIncident(String reason) {
        if (closed || !enabled) return false;
        long now = System.nanoTime();
        long previous = lastIncidentNanos.get();
        if ((previous != 0 && now - previous < TimeUnit.SECONDS.toNanos(10))
                || !lastIncidentNanos.compareAndSet(previous, now)
                || !incidentPending.compareAndSet(false, true)) {
            dropped.incrementAndGet();
            return false;
        }
        try {
            worker.execute(() -> {
                try { dump("incident"); }
                finally { incidentPending.set(false); }
            });
            return true;
        } catch (RuntimeException rejected) {
            incidentPending.set(false);
            dropped.incrementAndGet();
            return false;
        }
    }

    private void dump(String kind) {
        Recording current = recording;
        if (closed || current == null || current.getState() != RecordingState.RUNNING) return;
        Path temporary = null;
        try {
            // Reserve space before creating another snapshot, including failure paths.
            prune(ARCHIVE_FILES - 1, ARCHIVE_BYTES - MAX_SNAPSHOT_BYTES);
            if (Files.getFileStore(directory).getUsableSpace() < MIN_FREE_BYTES + MAX_SNAPSHOT_BYTES)
                throw new IOException("JFR snapshot skipped: cannot preserve 256 MiB free after bounded export");
            String name = "diag-" + boot + "-" + System.currentTimeMillis() + "-" + kind + ".jfr";
            Path destination = directory.resolve(name);
            temporary = directory.resolve(name + ".partial");
            current.dump(temporary);
            if (Files.size(temporary) > MAX_SNAPSHOT_BYTES)
                throw new IOException("JFR snapshot exceeded the bounded export size");
            try (FileChannel channel = FileChannel.open(temporary, StandardOpenOption.WRITE)) {
                channel.force(true);
            }
            atomicMove(temporary, destination);
            forceDirectory();
            long completedAt = System.currentTimeMillis();
            long bytes = Files.size(destination);
            String receipt = "{\"file\":\"" + name + "\",\"completedAtEpochMillis\":"
                    + completedAt + ",\"bytes\":" + bytes + ",\"dumpSequence\":" + (dumps + 1) + "}\n";
            forceReceipt(receipt);
            lastDump = name;
            lastDumpMillis = completedAt;
            dumps++;
            error = "";
            prune();
        } catch (Exception problem) {
            fail(problem);
        } finally {
            if (temporary != null) {
                try { Files.deleteIfExists(temporary); }
                catch (IOException problem) { fail(problem); }
            }
            try { prune(); }
            catch (IOException problem) { fail(problem); }
        }
    }

    private void forceReceipt(String receipt) throws IOException {
        Path temporary = directory.resolve("last-completed.json.partial");
        try (FileChannel channel = FileChannel.open(temporary, StandardOpenOption.CREATE,
                StandardOpenOption.TRUNCATE_EXISTING, StandardOpenOption.WRITE)) {
            ByteBuffer data = StandardCharsets.UTF_8.encode(receipt);
            while (data.hasRemaining()) channel.write(data);
            channel.force(true);
        }
        atomicMove(temporary, directory.resolve("last-completed.json"));
        forceDirectory();
    }

    private void recoverReceipt() throws IOException {
        Path receipt = directory.resolve("last-completed.json");
        if (!Files.isRegularFile(receipt, LinkOption.NOFOLLOW_LINKS) || Files.size(receipt) > 4096) return;
        String text = Files.readString(receipt);
        var match = Pattern.compile("\\\"file\\\"\\s*:\\s*\\\"(diag-[a-zA-Z0-9-]+\\.jfr)\\\"").matcher(text);
        if (!match.find()) return;
        Path previous = directory.resolve(match.group(1));
        if (!Files.isRegularFile(previous, LinkOption.NOFOLLOW_LINKS)
                || Files.size(previous) > MAX_SNAPSHOT_BYTES) return;
        lastDump = previous.getFileName().toString();
        var time = Pattern.compile("\\\"completedAtEpochMillis\\\"\\s*:\\s*([0-9]{1,16})").matcher(text);
        if (time.find()) lastDumpMillis = Long.parseLong(time.group(1));
        recoveredReceipt = true;
    }

    private void forceDirectory() {
        // Directory fsync is not provided by every Java filesystem implementation.
        try (FileChannel channel = FileChannel.open(directory, StandardOpenOption.READ)) {
            channel.force(true);
        } catch (IOException | UnsupportedOperationException ignored) {
            // Completed regular files remain forced; this is not a power-loss guarantee.
        }
    }

    private static void atomicMove(Path source, Path destination) throws IOException {
        try {
            Files.move(source, destination, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
        } catch (AtomicMoveNotSupportedException unsupported) {
            throw new IOException("Atomic publication unavailable; previous JFR receipt retained", unsupported);
        }
    }

    private void prune() throws IOException {
        prune(ARCHIVE_FILES, ARCHIVE_BYTES);
    }

    private void prune(int fileLimit, long byteLimit) throws IOException {
        List<Path> candidates = new ArrayList<>();
        try (var files = Files.list(directory)) {
            files.filter(path -> Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS))
                    .filter(path -> path.getFileName().toString().matches("diag-[a-zA-Z0-9-]+\\.jfr(?:\\.partial)?"))
                    .forEach(candidates::add);
        }
        candidates.sort(Comparator.comparingLong(JfrRecorder::modified));
        long bytes = 0;
        for (Path path : candidates) bytes += Files.size(path);
        int count = candidates.size();
        for (Path path : candidates) {
            if (count <= fileLimit && bytes <= byteLimit) break;
            if (path.getFileName().toString().equals(lastDump)) continue;
            long size = Files.size(path);
            Files.delete(path);
            bytes -= size;
            count--;
            pruned++;
        }
        archiveBytes = bytes;
        archiveFiles = count;
        if (count > fileLimit || bytes > byteLimit)
            throw new IOException("Unable to reserve bounded JFR archive space");
    }

    private static long modified(Path path) {
        try { return Files.getLastModifiedTime(path).toMillis(); }
        catch (IOException ignored) { return Long.MIN_VALUE; }
    }

    private void fail(Exception problem) {
        errors++;
        String message = problem.getClass().getSimpleName() + ": " + problem.getMessage();
        error = message.length() <= 512 ? message : message.substring(0, 512);
        LOG.log(System.Logger.Level.WARNING, "JFR monitoring: " + error);
    }

    public Map<String, Object> status() {
        Map<String, Object> status = new LinkedHashMap<>();
        Recording current = recording;
        status.put("enabled", enabled);
        status.put("recording", current != null && current.getState() == RecordingState.RUNNING);
        status.put("maxAgeSeconds", 1800);
        status.put("maxRecordingBytes", RECORDING_BYTES);
        status.put("maxArchiveBytes", ARCHIVE_BYTES);
        status.put("maxArchiveFiles", ARCHIVE_FILES);
        status.put("dumpCount", dumps);
        status.put("lastCompletedDump", lastDump);
        status.put("lastCompletedDumpEpochMillis", lastDumpMillis);
        status.put("recoveredPreviousReceipt", recoveredReceipt);
        status.put("incidentPending", incidentPending.get());
        status.put("droppedIncidentRequests", dropped.get());
        status.put("archiveBytes", archiveBytes);
        status.put("archiveFiles", archiveFiles);
        status.put("prunedFiles", pruned);
        status.put("errors", errors);
        status.put("error", error);
        status.put("durability", "Forced completed snapshots only; pending data is not acknowledged");
        return status;
    }

    @Override
    public synchronized void close() {
        if (closed) return;
        closed = true;
        enabled = false;
        // No shutdown dump is required for the durable-snapshot guarantee.
        worker.execute(() -> {
            Recording current = recording;
            if (current != null) current.close();
            recording = null;
            enabled = false;
        });
        worker.shutdown();
    }
}
