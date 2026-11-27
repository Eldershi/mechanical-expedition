package expedition.siftcompat;

import com.bawnorton.mixinsquared.adjuster.MixinAnnotationAdjusterRegistrar;
import java.util.List;
import java.util.Set;
import net.neoforged.fml.common.Mod;
import org.objectweb.asm.tree.ClassNode;
import org.spongepowered.asm.mixin.extensibility.IMixinConfigPlugin;
import org.spongepowered.asm.mixin.extensibility.IMixinInfo;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mod("expedition_sift_compat")
public final class SiftMixinPlugin implements IMixinConfigPlugin {
    private static final String SIFT_MENU = "mielon.thesift.mixin.EnchantmentMenuMixin";
    private static final String SIFT_MAP = "mielon.thesift.mixin.SiftMapItemMixin";

    @Override
    public void onLoad(String mixinPackage) {
        MixinAnnotationAdjusterRegistrar.register((targets, mixin, method, annotation) -> {
            boolean fuelRedirect = mixin.equals(SIFT_MENU) && method.name.equals("theSift$quickMoveCharoite");
            boolean mapRedirect = mixin.equals(SIFT_MAP) && method.name.equals("theSift$storeActualBlockColor");
            return (fuelRedirect || mapRedirect) && annotation.is(Redirect.class) ? null : annotation;
        });
    }

    @Override public String getRefMapperConfig() { return null; }
    @Override public boolean shouldApplyMixin(String target, String mixin) { return true; }
    @Override public void acceptTargets(Set<String> own, Set<String> other) {}
    @Override public List<String> getMixins() { return null; }
    @Override public void preApply(String target, ClassNode node, String mixin, IMixinInfo info) {}
    @Override public void postApply(String target, ClassNode node, String mixin, IMixinInfo info) {}
}
