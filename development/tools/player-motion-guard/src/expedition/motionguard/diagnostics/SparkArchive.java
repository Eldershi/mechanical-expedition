package expedition.motionguard.diagnostics;

import com.google.gson.Gson;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;
import net.minecraft.server.MinecraftServer;
import net.minecraftforge.fml.ModList;

/** Exports the enabled Spark background profiler through its public command. */
public final class SparkArchive implements AutoCloseable {
    private static final String COMMAND = "spark profiler stop --save-to-file";
    private static final String SCHEMA = "expedition-spark-archive/1";
    private static final long FILE_LIMIT = 32L << 20, TOTAL_LIMIT = 128L << 20;
    private static final long SOURCE_LIMIT = 256L << 20;
    private static final long WINDOW = TimeUnit.SECONDS.toNanos(60);
    private static final int SCAN_LIMIT = 512, FILES_LIMIT = 8;
    private final Path directory;
    private final Path sparkDirectory = Path.of("config/spark").toAbsolutePath().normalize();
    private final ScheduledThreadPoolExecutor worker;
    private final Object lock = new Object();
    private final boolean sparkPresent;
    private final AtomicLong requested = new AtomicLong(), observed = new AtomicLong();
    private final AtomicLong confirmed = new AtomicLong(), deleted = new AtomicLong();
    private final AtomicLong ambiguous = new AtomicLong(), errors = new AtomicLong(), pruned = new AtomicLong();
    private final AtomicLong controlGeneration = new AtomicLong();
    private volatile boolean checked, backgroundEnabled, closed;
    private volatile boolean blocked, resumePending, sourceScanCapped;
    private volatile long firstTick, nextRequestNanos, pausedUntilNanos, archiveBytes, archiveFiles;
    private volatile long sourceProfileBytes;
    private volatile int sourceScannedEntries;
    private volatile String lastError = "", lastArchive = "", blockedReason = "";
    private volatile Request request;
    private Map<Path, Stamp> seen = Map.of();
    private final Gson gson = new Gson();

    private record Stamp(long size, long modified, Object key) {}
    private record Scan(Map<Path, Stamp> files, boolean capped, long bytes, int entries) {}
    private static final class Candidate {
        Stamp stamp; int stable = 1;
        Candidate(Stamp stamp) { this.stamp = stamp; }
    }
    private static final class Request {
        volatile Map<Path, Stamp> baseline = Map.of();
        volatile boolean ready, issued, cancelled;
        volatile long millis, nanos, sequence;
        final Map<Path, Candidate> candidates = new LinkedHashMap<>();
    }

    public SparkArchive(Path archiveDirectory) {
        directory = archiveDirectory.toAbsolutePath().normalize();
        boolean present;
        try { present = ModList.get().isLoaded("spark"); }
        catch (RuntimeException problem) { present = false; fail(problem); }
        sparkPresent = present;
        worker = new ScheduledThreadPoolExecutor(1, task -> {
            Thread thread = new Thread(task, "Expedition-Diagnostics-SparkArchive");
            thread.setDaemon(true); return thread;
        });
        worker.setRemoveOnCancelPolicy(true);
        worker.setExecuteExistingDelayedTasksAfterShutdownPolicy(false);
        worker.setContinueExistingPeriodicTasksAfterShutdownPolicy(false);
        worker.scheduleWithFixedDelay(this::poll, 0, 5, TimeUnit.SECONDS);
    }

    /** The tick thread performs no filesystem operations. */
    public void serverTick(MinecraftServer server) {
        long now = System.nanoTime();
        if (firstTick == 0) { firstTick = now; nextRequestNanos = now + TimeUnit.SECONDS.toNanos(45); }
        if (closed || blocked || resumePending || !sparkPresent || !checked || !backgroundEnabled || now < pausedUntilNanos) return;
        Request current = request;
        if (current != null) {
            if (!current.ready || current.issued || current.cancelled) return;
            synchronized (lock) {
                if (closed || blocked || resumePending || request != current || current.issued || current.cancelled
                        || System.nanoTime() < pausedUntilNanos) return;
                current.millis = System.currentTimeMillis(); current.nanos = System.nanoTime();
                current.sequence = requested.incrementAndGet(); current.issued = true;
                nextRequestNanos = current.nanos + TimeUnit.SECONDS.toNanos(300);
            }
            try { server.m_129892_().m_230957_(server.m_129893_(), COMMAND); }
            catch (RuntimeException | LinkageError problem) { current.cancelled = true; block("command_failed"); fail(problem); }
            return;
        }
        if (now < nextRequestNanos) return;
        synchronized (lock) {
            if (request != null || closed || blocked || resumePending) return;
            Request prepared = new Request(); request = prepared;
            worker.execute(() -> prepare(prepared));
        }
    }

    private void prepare(Request prepared) {
        try {
            Scan scan = sources();
            if (!withinSourceBudget(scan)) { finish(prepared); return; }
            prepared.baseline = Map.copyOf(scan.files());
            prepared.ready = true;
        } catch (Exception problem) {
            ambiguous.incrementAndGet(); block("source_preflight_failed"); fail(problem); finish(prepared);
            nextRequestNanos = System.nanoTime() + TimeUnit.SECONDS.toNanos(300);
        }
    }

    private void poll() {
        if (closed) return;
        try {
            if (!checked) {
                if (sparkPresent) {
                    Path config = sparkDirectory.resolve("config.json");
                    if (!Files.isRegularFile(config, LinkOption.NOFOLLOW_LINKS) || Files.size(config) > 65536)
                        throw new IOException("Missing or oversized Spark configuration");
                    var json = JsonParser.parseString(Files.readString(config)).getAsJsonObject();
                    backgroundEnabled = json.has("backgroundProfiler") && json.get("backgroundProfiler").isJsonPrimitive()
                            && json.get("backgroundProfiler").getAsJsonPrimitive().isBoolean()
                            && json.get("backgroundProfiler").getAsBoolean();
                }
                Scan initial = sources(); seen = Map.copyOf(initial.files());
                withinSourceBudget(initial);
                Files.createDirectories(directory); retain(0, 0); checked = true;
                return;
            }
            Scan scan = sources();
            Request current = request;
            boolean active = current != null && current.issued && !current.cancelled;
            if (!withinSourceBudget(scan) && current != null) current.cancelled = true;
            for (var entry : scan.files().entrySet()) {
                Path path = entry.getKey(); Stamp stamp = entry.getValue();
                boolean fresh = !seen.containsKey(path);
                if (fresh) observed.incrementAndGet();
                boolean attributable = active && !current.baseline.containsKey(path)
                        && stamp.modified() >= current.millis && stamp.modified() <= current.millis + 60000;
                if (attributable) {
                    Candidate candidate = current.candidates.get(path);
                    if (candidate == null) current.candidates.put(path, new Candidate(stamp));
                    else { candidate.stable = candidate.stamp.equals(stamp) ? candidate.stable + 1 : 1; candidate.stamp = stamp; }
                } else if (fresh) ambiguous.incrementAndGet();
            }
            seen = Map.copyOf(scan.files());
            if (current == null) return;
            if (current.cancelled) {
                ambiguous.addAndGet(Math.max(1, current.candidates.size()));
                if (current.issued && !blocked) block("issued_request_cancelled");
                finish(current); return;
            }
            if (!current.issued || System.nanoTime() - current.nanos < WINDOW) return;
            if (current.candidates.size() != 1) {
                ambiguous.addAndGet(Math.max(1, current.candidates.size()));
                block(current.candidates.isEmpty() ? "profile_not_observed" : "ambiguous_outputs");
            }
            else {
                var entry = current.candidates.entrySet().iterator().next();
                Candidate candidate = entry.getValue();
                if (candidate.stable < 2 || !candidate.stamp.equals(scan.files().get(entry.getKey()))) {
                    ambiguous.incrementAndGet(); block("profile_unstable_or_missing");
                }
                else archive(current, entry.getKey(), candidate.stamp);
            }
            finish(current);
        } catch (Exception | LinkageError problem) {
            fail(problem);
            if (!checked) checked = true;
            block("source_or_archive_io_error");
            Request current = request;
            if (current != null) { current.cancelled = true; finish(current); }
        }
    }

    private Scan sources() throws IOException {
        Map<Path, Stamp> found = new LinkedHashMap<>(); int scanned = 0; long bytes = 0;
        for (Path parent : List.of(sparkDirectory, sparkDirectory.resolve("profiles"))) {
            if (!Files.isDirectory(parent, LinkOption.NOFOLLOW_LINKS)) continue;
            try (DirectoryStream<Path> entries = Files.newDirectoryStream(parent)) {
                for (Path path : entries) {
                    if (++scanned > SCAN_LIMIT) return new Scan(found, true, bytes, SCAN_LIMIT);
                    if (!path.getFileName().toString().endsWith(".sparkprofile")
                            || !Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) continue;
                    Stamp stamp = stamp(path); found.put(path, stamp);
                    bytes = stamp.size() > Long.MAX_VALUE - bytes ? Long.MAX_VALUE : bytes + stamp.size();
                }
            }
        }
        return new Scan(found, false, bytes, scanned);
    }

    private boolean withinSourceBudget(Scan scan) {
        sourceProfileBytes = scan.bytes(); sourceScannedEntries = scan.entries(); sourceScanCapped = scan.capped();
        if (scan.capped()) { block("source_entry_budget_exceeded"); return false; }
        if (scan.bytes() > SOURCE_LIMIT) { block("source_byte_budget_exceeded"); return false; }
        return true;
    }

    private static Stamp stamp(Path path) throws IOException {
        BasicFileAttributes attributes = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!attributes.isRegularFile()) throw new IOException("Spark source is not a regular file");
        return new Stamp(attributes.size(), attributes.lastModifiedTime().toMillis(), attributes.fileKey());
    }

    private void archive(Request owner, Path source, Stamp original) throws Exception {
        if (original.size() <= 0 || original.size() > FILE_LIMIT) {
            ambiguous.incrementAndGet(); block("profile_empty_or_oversize"); return;
        }
        Files.createDirectories(directory); retain(original.size(), 1);
        String name = "expedition-spark-" + System.currentTimeMillis() + "-" + UUID.randomUUID() + ".sparkprofile";
        Path destination = directory.resolve(name), temporary = directory.resolve(name + ".partial");
        Path receipt = directory.resolve(name + ".receipt.json"), receiptTemporary = directory.resolve(name + ".receipt.partial");
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256"); long copied = 0;
            try (FileChannel input = FileChannel.open(source, StandardOpenOption.READ, LinkOption.NOFOLLOW_LINKS);
                 FileChannel output = FileChannel.open(temporary, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                ByteBuffer buffer = ByteBuffer.allocate(65536);
                while (input.read(buffer) != -1) {
                    buffer.flip(); copied += buffer.remaining();
                    if (copied > FILE_LIMIT) throw new IOException("Spark profile grew beyond limit");
                    digest.update(buffer.asReadOnlyBuffer());
                    while (buffer.hasRemaining()) output.write(buffer);
                    buffer.clear();
                }
                output.force(true);
            }
            if (closed || owner.cancelled || copied != original.size() || !original.equals(stamp(source)))
                throw new IOException("Spark profile changed while copying");
            Files.move(temporary, destination, StandardCopyOption.ATOMIC_MOVE);
            boolean directoryForced = forceDirectory(directory);
            Map<String, Object> values = new LinkedHashMap<>();
            values.put("schema", SCHEMA); values.put("file", name); values.put("bytes", copied);
            values.put("sha256", HexFormat.of().formatHex(digest.digest()));
            values.put("requestSequence", owner.sequence); values.put("requestEpochMillis", owner.millis);
            values.put("confirmedEpochMillis", System.currentTimeMillis());
            byte[] bytes = (gson.toJson(values) + "\n").getBytes(StandardCharsets.UTF_8);
            try (FileChannel output = FileChannel.open(receiptTemporary, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
                ByteBuffer buffer = ByteBuffer.wrap(bytes); while (buffer.hasRemaining()) output.write(buffer);
                output.force(true);
            }
            Files.move(receiptTemporary, receipt, StandardCopyOption.ATOMIC_MOVE);
            directoryForced &= forceDirectory(directory);
            if (!Arrays.equals(bytes, Files.readAllBytes(receipt))) throw new IOException("Spark receipt verification failed");
            confirmed.incrementAndGet(); lastArchive = name;
            // Uncertain attribution or durability always leaves the original untouched.
            if (!closed && !owner.cancelled && directoryForced && original.equals(stamp(source))) {
                Files.delete(source); deleted.incrementAndGet(); forceDirectory(source.getParent());
            } else { ambiguous.incrementAndGet(); block("source_cleanup_not_confirmed"); }
            retain(0, 0);
        } finally {
            Files.deleteIfExists(temporary); Files.deleteIfExists(receiptTemporary);
        }
    }

    /** Prunes only archives with this writer's matching receipt; foreign files are retained. */
    private void retain(long reserveBytes, int reserveFiles) throws IOException {
        List<Path> profiles = new ArrayList<>(); long bytes = 0; int entries = 0;
        try (DirectoryStream<Path> files = Files.newDirectoryStream(directory)) {
            for (Path path : files) {
                if (++entries > SCAN_LIMIT) throw new IOException("Spark archive scan limit");
                if (!Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS)) continue;
                bytes += Files.size(path);
                if (path.getFileName().toString().endsWith(".sparkprofile")) profiles.add(path);
            }
        }
        profiles.sort(Comparator.comparing(path -> path.getFileName().toString()));
        int count = profiles.size();
        for (Path profile : profiles) {
            if (count + reserveFiles <= FILES_LIMIT && bytes + reserveBytes + 8192 <= TOTAL_LIMIT) break;
            String name = profile.getFileName().toString();
            Path receipt = directory.resolve(name + ".receipt.json");
            if (!name.matches("expedition-spark-[0-9]+-[a-f0-9-]+\\.sparkprofile")
                    || !Files.isRegularFile(receipt, LinkOption.NOFOLLOW_LINKS) || Files.size(receipt) > 4096) continue;
            try {
                var metadata = JsonParser.parseString(Files.readString(receipt)).getAsJsonObject();
                if (!SCHEMA.equals(metadata.get("schema").getAsString()) || !name.equals(metadata.get("file").getAsString())) continue;
            } catch (RuntimeException invalid) { continue; }
            long removed = Files.size(profile) + Files.size(receipt);
            Files.delete(profile); Files.delete(receipt); bytes -= removed; count--; pruned.incrementAndGet();
        }
        archiveBytes = bytes; archiveFiles = count;
        if (count + reserveFiles > FILES_LIMIT || bytes + reserveBytes + 8192 > TOTAL_LIMIT)
            throw new IOException("Spark archive capacity blocked by unowned files");
    }

    private static boolean forceDirectory(Path path) {
        try (FileChannel channel = FileChannel.open(path, StandardOpenOption.READ)) { channel.force(true); return true; }
        catch (IOException | UnsupportedOperationException unsupported) { return false; }
    }

    private void finish(Request owner) { synchronized (lock) { if (request == owner) request = null; } }
    private void fail(Throwable problem) { errors.incrementAndGet(); lastError = problem.getClass().getSimpleName(); }
    private void block(String reason) { synchronized (lock) { blocked = true; blockedReason = reason; } }

    public void pauseForMinutes(int minutes) {
        long now = System.nanoTime();
        long generation;
        synchronized (lock) {
            generation = controlGeneration.incrementAndGet();
            pausedUntilNanos = minutes <= 0 ? 0 : now + TimeUnit.MINUTES.toNanos(Math.min(minutes, 1440));
            nextRequestNanos = now + TimeUnit.SECONDS.toNanos(45);
            Request current = request;
            if (current != null) { current.cancelled = true; if (current.issued) block("issued_request_cancelled_by_pause"); }
            resumePending = minutes <= 0;
            if (resumePending) block("resume_preflight_pending");
        }
        if (minutes <= 0 && !closed) worker.execute(() -> resume(generation));
    }

    private void resume(long generation) {
        try {
            if (closed || controlGeneration.get() != generation) return;
            Request old = request;
            if (old != null) { if (old.issued) ambiguous.addAndGet(Math.max(1, old.candidates.size())); finish(old); }
            Scan scan = sources();
            if (!withinSourceBudget(scan)) return;
            Files.createDirectories(directory); retain(0, 0);
            synchronized (lock) {
                if (closed || controlGeneration.get() != generation) return;
                blocked = false; blockedReason = "";
                nextRequestNanos = System.nanoTime() + TimeUnit.SECONDS.toNanos(45);
            }
        } catch (Exception problem) { block("resume_preflight_failed"); fail(problem); }
        finally { if (controlGeneration.get() == generation) resumePending = false; }
    }

    public Map<String, Object> status() {
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("sparkPresent", sparkPresent); values.put("configurationChecked", checked);
        values.put("backgroundProfilerEnabled", backgroundEnabled); values.put("closed", closed);
        values.put("blocked", blocked); values.put("blockedReason", blockedReason); values.put("resumePending", resumePending);
        values.put("sourceProfileBytes", sourceProfileBytes); values.put("sourceScannedEntries", sourceScannedEntries);
        values.put("sourceScanCapped", sourceScanCapped); values.put("sourceBudgetBytes", SOURCE_LIMIT);
        values.put("requested", requested.get()); values.put("observed", observed.get());
        values.put("confirmed", confirmed.get()); values.put("deleted", deleted.get());
        values.put("ambiguous", ambiguous.get()); values.put("errors", errors.get()); values.put("pruned", pruned.get());
        values.put("paused", System.nanoTime() < pausedUntilNanos);
        values.put("pauseRemainingSeconds", Math.max(0, TimeUnit.NANOSECONDS.toSeconds(pausedUntilNanos - System.nanoTime())));
        Request current = request;
        values.put("pending", current == null ? "none" : current.issued ? "observing" : current.ready ? "ready" : "preparing");
        values.put("archiveFiles", archiveFiles); values.put("archiveBytes", archiveBytes);
        values.put("lastArchive", lastArchive); values.put("lastError", lastError);
        return Collections.unmodifiableMap(values);
    }

    @Override public void close() {
        synchronized (lock) { closed = true; Request current = request; if (current != null) current.cancelled = true; }
        worker.shutdownNow();
    }
}
