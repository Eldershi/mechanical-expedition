package expedition.maidguard;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Startup-only policy. No world storage, markers, structures or generation settings are written. */
public final class WorldAgeGuard {
    private static final Logger LOGGER=LoggerFactory.getLogger("ExpeditionMaidWorldgenGuard");
    private WorldAgeGuard() {}
    public static boolean existingWorld(long gameTime) { return gameTime>0L; }
    public static void blocked(long gameTime) {
        LOGGER.warn("[MaidWorldgenGuard] Blocked Stellar Endshore automatic fixed placement in an existing world (overworld gameTime={}). Existing markers and natural chunk generation are unchanged.",gameTime);
    }
}
