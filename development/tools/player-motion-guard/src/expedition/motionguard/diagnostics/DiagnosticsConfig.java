package expedition.motionguard.diagnostics;

import com.google.gson.GsonBuilder;
import java.nio.file.*;

/** Fixed output location and bounded, operator-adjustable recording budgets. */
public final class DiagnosticsConfig {
    public boolean enabled = true;
    public boolean jfrEnabled = true;
    public boolean watchdogEnabled = true;
    public boolean sparkExportEnabled = true;
    public int stateSampleEveryTicks = 1;
    public int equipmentCheckEveryTicks = 20;
    public int statePersistEveryTicks = 20;
    public int ringSamplesPerPlayer = 1200;
    public int maxTrackedPlayers = 32;
    public int queueCapacity = 2048;
    public int flushIntervalMillis = 1000;
    public int forceIntervalMillis = 5000;
    public long eventFileBytes = 8L << 20;
    public long totalLogBytes = 128L << 20;
    public int maxLogFiles = 16;
    public long watchdogStallMillis = 10000;
    public long watchdogRepeatMillis = 30000;
    public int maxIncidentFiles = 8;
    public long maxIncidentBytes = 32L << 20;
    public String configurationError = "";

    public static DiagnosticsConfig load(Path file) {
        DiagnosticsConfig config = new DiagnosticsConfig();
        var gson = new GsonBuilder().setPrettyPrinting().create();
        try {
            if (Files.exists(file)) {
                if (Files.size(file) > 65536) throw new IllegalArgumentException("Configuration exceeds 64 KiB");
                DiagnosticsConfig parsed = gson.fromJson(Files.readString(file), DiagnosticsConfig.class);
                if (parsed == null) throw new IllegalArgumentException("Empty configuration");
                config = parsed;
            } else {
                Files.createDirectories(file.toAbsolutePath().getParent());
                Files.writeString(file, gson.toJson(config) + "\n", StandardOpenOption.CREATE_NEW);
            }
        } catch (Exception problem) {
            config.configurationError = problem.getClass().getSimpleName();
            config.enabled=false;
        }
        config.stateSampleEveryTicks = bound(config.stateSampleEveryTicks, 1, 200);
        config.equipmentCheckEveryTicks = bound(config.equipmentCheckEveryTicks, 5, 1200);
        config.statePersistEveryTicks = bound(config.statePersistEveryTicks, 1, 1200);
        config.ringSamplesPerPlayer = bound(config.ringSamplesPerPlayer, 20, 2400);
        config.maxTrackedPlayers = bound(config.maxTrackedPlayers, 1, 128);
        config.queueCapacity = bound(config.queueCapacity, 64, 8192);
        config.flushIntervalMillis = bound(config.flushIntervalMillis, 100, 5000);
        config.forceIntervalMillis = bound(config.forceIntervalMillis, 1000, 30000);
        config.totalLogBytes = bound(config.totalLogBytes, 1L << 20, 256L << 20);
        config.eventFileBytes = bound(config.eventFileBytes, 65536, Math.min(16L << 20, config.totalLogBytes / 2));
        config.maxLogFiles = bound(config.maxLogFiles, 2, 64);
        config.watchdogStallMillis = bound(config.watchdogStallMillis, 1000, 120000);
        config.watchdogRepeatMillis = bound(config.watchdogRepeatMillis, 5000, 300000);
        config.maxIncidentFiles = bound(config.maxIncidentFiles, 1, 32);
        config.maxIncidentBytes = bound(config.maxIncidentBytes, 1L << 20, 128L << 20);
        return config;
    }

    private static int bound(int value, int low, int high) { return Math.max(low, Math.min(high, value)); }
    private static long bound(long value, long low, long high) { return Math.max(low, Math.min(high, value)); }
}
