package expedition.motionguard.diagnostics;

/** Immutable values only: safe for background serialization and watchdog reads. */
public record PlayerSnapshot(long tick, long timeMillis, String playerId, int entityId,
        String dimension, double x, double y, double z, double motionX, double motionY, double motionZ,
        double minX, double minY, double minZ, double maxX, double maxY, double maxZ,
        float yaw, float pitch, String pose, int flags, float fallDistance, long equipmentVersion, long equipmentCapturedTick) {}
