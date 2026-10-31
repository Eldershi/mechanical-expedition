package expedition.teleport.railwayperf.mixin;

import expedition.teleport.railwayperf.ExactHeightMemoizer;
import expedition.teleport.railwayperf.SamplerInternals;

import com.xkmxz.tongdarailway_for_forge.util.AdaptiveHeightSampler;

import com.xkmxz.tongdarailway_for_forge.Config;
import com.xkmxz.tongdarailway_for_forge.railway.RegionPos;
import com.xkmxz.tongdarailway_for_forge.railway.planner.RoutePlanner;
import net.minecraft.server.level.ServerLevel;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = RoutePlanner.class, remap = false)
public abstract class RoutePlannerHeightCacheMixin {
    @Redirect(method = "getHeightMap", at = @At(value = "NEW",
        target = "com/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler"), require = 1)
    private AdaptiveHeightSampler expedition$memoizedSampler(double threshold, int maxLevel,
            int samplesPerNode, AdaptiveHeightSampler.HeightFunction heightFunction,
            ServerLevel level, RegionPos region) {
        var memo = new ExactHeightMemoizer(heightFunction::getHeight,
            region.x(), region.z(), Config.chunkGroupSize);
        return new AdaptiveHeightSampler(threshold, maxLevel, samplesPerNode, memo);
    }
}
