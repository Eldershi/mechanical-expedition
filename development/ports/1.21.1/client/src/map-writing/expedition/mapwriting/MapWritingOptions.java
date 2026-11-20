package expedition.mapwriting;

import com.mojang.logging.LogUtils;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.NoSuchFileException;
import java.util.Properties;
import net.neoforged.fml.loading.FMLPaths;

public final class MapWritingOptions {
    public static final boolean PAUSE_SINGLEPLAYER_BACKGROUND = loadPauseSetting();

    private MapWritingOptions() {}

    private static boolean loadPauseSetting() {
        var path = FMLPaths.CONFIGDIR.get().resolve("expedition-map-writing.properties");
        var properties = new Properties();
        try (var reader = Files.newBufferedReader(path)) {
            properties.load(reader);
            return Boolean.parseBoolean(properties.getProperty("pause_singleplayer_background", "false"));
        } catch (NoSuchFileException missing) {
            return false;
        } catch (IOException | IllegalArgumentException error) {
            LogUtils.getLogger().warn("Could not read Expedition's singleplayer map settings", error);
            return false;
        }
    }
}
