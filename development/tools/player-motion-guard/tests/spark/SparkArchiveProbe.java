package expedition.motionguard.tests;

import com.google.gson.Gson;
import expedition.motionguard.diagnostics.SparkArchive;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.Map;
import java.util.concurrent.ScheduledThreadPoolExecutor;
import java.util.concurrent.TimeUnit;
import net.minecraft.server.MinecraftServer;

/** Exercises production archive decisions with real local files and a command sink. */
public final class SparkArchiveProbe {
    private static Object get(Object target, String name) throws Exception {
        Field field = target.getClass().getDeclaredField(name); field.setAccessible(true); return field.get(target);
    }
    private static void set(Object target, String name, long value) throws Exception {
        Field field = target.getClass().getDeclaredField(name); field.setAccessible(true); field.setLong(target, value);
    }
    private static void check(boolean condition, String reason) { if (!condition) throw new AssertionError(reason); }
    private static void barrier(ScheduledThreadPoolExecutor worker) throws Exception { worker.submit(() -> {}).get(5, TimeUnit.SECONDS); }
    private static void poll(SparkArchive archive, ScheduledThreadPoolExecutor worker) throws Exception {
        Method method = SparkArchive.class.getDeclaredMethod("poll"); method.setAccessible(true);
        worker.submit(() -> { try { method.invoke(archive); } catch (Exception error) { throw new RuntimeException(error); } }).get(5, TimeUnit.SECONDS);
    }
    private static void due(SparkArchive archive) throws Exception {
        set(archive, "firstTick", System.nanoTime() - TimeUnit.SECONDS.toNanos(46));
        set(archive, "nextRequestNanos", System.nanoTime() - 1);
    }
    private static void request(SparkArchive archive, MinecraftServer server, ScheduledThreadPoolExecutor worker) throws Exception {
        due(archive); archive.serverTick(server); barrier(worker); archive.serverTick(server);
    }
    private static void expire(SparkArchive archive) throws Exception {
        set(get(archive, "request"), "nanos", System.nanoTime() - TimeUnit.SECONDS.toNanos(61));
    }
    private static void sparse(Path file, long bytes) throws Exception {
        try (FileChannel channel = FileChannel.open(file, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            channel.position(bytes - 1); channel.write(ByteBuffer.wrap(new byte[]{1}));
        }
    }
    private static void staysBlocked(SparkArchive archive, MinecraftServer server, int commands) throws Exception {
        for (int i = 0; i < 100; i++) { due(archive); archive.serverTick(server); }
        check(server.commandCount == commands, "blocked recorder issued another command");
        check(Boolean.TRUE.equals(archive.status().get("blocked")), "missing blocked status");
    }
    public static void main(String[] args) throws Exception {
        String scenario = args[0];
        Path source = Path.of("config/spark"); Files.createDirectories(source);
        Files.writeString(source.resolve("config.json"), "{\"backgroundProfiler\":true}\n");
        if (scenario.equals("healthy-history")) sparse(source.resolve("historical.sparkprofile"), 190L << 20);
        SparkArchive archive = new SparkArchive(Path.of("archive"));
        MinecraftServer server = new MinecraftServer();
        ScheduledThreadPoolExecutor worker = (ScheduledThreadPoolExecutor) get(archive, "worker");
        try {
            barrier(worker);
            check(Boolean.TRUE.equals(archive.status().get("configurationChecked")), "startup not checked");
            // All observation times below are controlled explicitly, without real timer waits.
            Thread.sleep(20); worker.getQueue().clear();
            if (scenario.equals("source-bytes") || scenario.equals("source-entries")) {
                if (scenario.equals("source-bytes")) sparse(source.resolve("manual.sparkprofile"), (256L << 20) + 1);
                else for (int i=0;i<513;i++) Files.writeString(source.resolve("manual-"+i+".sparkprofile"), "x");
                request(archive, server, worker); staysBlocked(archive, server, 0);
                archive.pauseForMinutes(0); barrier(worker);
                check(!Boolean.TRUE.equals(archive.status().get("resumePending")), "resume preflight unfinished");
                staysBlocked(archive, server, 0);
                check(String.valueOf(archive.status().get("blockedReason")).startsWith("source_"), "budget reason missing");
                if (scenario.equals("source-bytes")) {
                    Files.delete(source.resolve("manual.sparkprofile"));
                    archive.pauseForMinutes(0); barrier(worker);
                    check(Boolean.FALSE.equals(archive.status().get("blocked")), "valid resume did not clear block");
                    check(server.commandCount==0, "resume itself issued command");
                    check((long)get(archive,"nextRequestNanos")>System.nanoTime(), "resume buffer absent");
                }
            } else {
                request(archive, server, worker);
                check(server.commandCount==1, "first command missing");
                check(server.lastCommand.equals("spark profiler stop --save-to-file"), "command changed");
                if (scenario.equals("oversize")) sparse(source.resolve("own.sparkprofile"), (32L << 20) + 1);
                else Files.writeString(source.resolve("own.sparkprofile"), "test-profile");
                if (scenario.equals("ambiguous")) Files.writeString(source.resolve("manual.sparkprofile"), "other-profile");
                if (scenario.equals("archive-failure")) { Files.delete(Path.of("archive")); Files.writeString(Path.of("archive"), "blocked directory"); }
                poll(archive, worker); poll(archive, worker); expire(archive); poll(archive, worker);
                if (scenario.equals("healthy-history")) {
                    check(((Number)archive.status().get("confirmed")).longValue()==1, "archive confirmation missing");
                    check(((Number)archive.status().get("deleted")).longValue()==1, "unique confirmed source not deleted");
                    check(Boolean.FALSE.equals(archive.status().get("blocked")), "successful cycle blocked");
                    check(!Files.exists(source.resolve("own.sparkprofile")), "own source retained unexpectedly");
                    check(Files.size(source.resolve("historical.sparkprofile"))==(190L << 20), "historical source changed");
                } else {
                    staysBlocked(archive, server, 1);
                    check(Files.exists(source.resolve("own.sparkprofile")), "failed cycle removed source");
                    check(((Number)archive.status().get("deleted")).longValue()==0, "false source deletion ACK");
                }
            }
            System.out.println(new Gson().toJson(Map.of("scenario",scenario,"passed",true,"commands",server.commandCount,"status",archive.status())));
        } finally { archive.close(); worker.awaitTermination(5, TimeUnit.SECONDS); }
    }
}
