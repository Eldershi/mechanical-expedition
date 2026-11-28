package expedition.performance.support;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Set;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.shaderpack.ShaderPack;

public final class BslProfile {
    private static final Set<String> SUPPORTED_ARCHIVES = Set.of(
        "8b1a001759a7e5dcd55abbad441ada111460d0b59618dccf3254407ac365a580",
        "6a90982bbc4d4a7a829dd394cb4e17004977218222d379088b5bdc9e07954221"
    );

    private BslProfile() {}

    public static boolean hasDisabledOptions(ShaderPack pack, String first, String second) {
        var options = pack.getShaderPackOptions().getOptionValues();
        var declared = options.getOptionSet().getBooleanOptions();
        return declared.containsKey(first) && declared.containsKey(second)
            && !options.getBooleanValueOrDefault(first) && !options.getBooleanValueOrDefault(second);
    }

    public static boolean isSupportedArchive() {
        var name = Iris.getCurrentPackName();
        if (name == null || !name.endsWith(".zip") || !Path.of(name).getFileName().toString().equals(name)) {
            return false;
        }
        var pack = Iris.getShaderpacksDirectory().resolve(name);
        try {
            if (!Files.isRegularFile(pack) || Files.size(pack) > 2_000_000) {
                return false;
            }
            var digest = MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(pack));
            return SUPPORTED_ARCHIVES.contains(HexFormat.of().formatHex(digest));
        } catch (IOException | NoSuchAlgorithmException ignored) {
            return false;
        }
    }
}
