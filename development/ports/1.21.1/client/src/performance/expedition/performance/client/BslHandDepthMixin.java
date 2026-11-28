package expedition.performance.client;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Set;
import net.irisshaders.iris.Iris;
import net.irisshaders.iris.pipeline.IrisRenderingPipeline;
import net.irisshaders.iris.shaderpack.programs.ProgramSet;
import net.irisshaders.iris.targets.RenderTargets;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = IrisRenderingPipeline.class, remap = false)
abstract class BslHandDepthMixin {
    @Unique
    private static final Set<String> expedition$knownBslArchives = Set.of(
        "8b1a001759a7e5dcd55abbad441ada111460d0b59618dccf3254407ac365a580",
        "6a90982bbc4d4a7a829dd394cb4e17004977218222d379088b5bdc9e07954221"
    );

    @Unique
    private boolean expedition$skipUnusedHandDepth;

    @Inject(method = "<init>(Lnet/irisshaders/iris/shaderpack/programs/ProgramSet;)V", at = @At("RETURN"))
    private void expedition$checkHandDepthConsumers(ProgramSet programs, CallbackInfo callback) {
        var options = programs.getPack().getShaderPackOptions().getOptionValues();
        var declared = options.getOptionSet().getBooleanOptions();
        // BSL's only consumers of depthtex2 are the motion blur and depth of field passes.
        expedition$skipUnusedHandDepth = declared.containsKey("MOTION_BLUR")
            && declared.containsKey("DOF")
            && !options.getBooleanValueOrDefault("MOTION_BLUR")
            && !options.getBooleanValueOrDefault("DOF")
            && expedition$isKnownBslArchive();
    }

    @Redirect(
        method = "beginHand()V",
        at = @At(value = "INVOKE", target = "Lnet/irisshaders/iris/targets/RenderTargets;copyPreHandDepth()V")
    )
    private void expedition$copyHandDepthWhenUsed(RenderTargets targets) {
        if (!expedition$skipUnusedHandDepth) {
            targets.copyPreHandDepth();
        }
    }

    @Unique
    private static boolean expedition$isKnownBslArchive() {
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
            return expedition$knownBslArchives.contains(HexFormat.of().formatHex(digest));
        } catch (IOException | NoSuchAlgorithmException ignored) {
            return false;
        }
    }
}
