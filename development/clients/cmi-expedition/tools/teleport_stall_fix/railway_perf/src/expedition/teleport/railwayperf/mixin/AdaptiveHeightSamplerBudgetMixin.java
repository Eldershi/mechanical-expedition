package expedition.teleport.railwayperf.mixin;

import expedition.teleport.railwayperf.ExactHeightMemoizer;
import expedition.teleport.railwayperf.SamplerInternals;

import com.xkmxz.tongdarailway_for_forge.util.AdaptiveHeightSampler;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicInteger;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Coerce;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/**
 * All noise calls, including the root node, share a two-worker CPU budget.
 * Workers only sample/enqueue children and return; only planner callers await
 * the completion latch, so recursively scheduling children cannot deadlock.
 */
@Mixin(value = AdaptiveHeightSampler.class, remap = false)
public abstract class AdaptiveHeightSamplerBudgetMixin {
    @Shadow @Final private ExecutorService executor;
    @Unique private volatile Throwable expedition$sampleFailure;

    @Redirect(method = "<clinit>", at = @At(value = "INVOKE",
        target = "Ljava/util/concurrent/Executors;newCachedThreadPool()Ljava/util/concurrent/ExecutorService;"),
        require = 1)
    private static ExecutorService expedition$boundedSamplingPool() {
        AtomicInteger ids = new AtomicInteger();
        return Executors.newFixedThreadPool(2, runnable -> {
            Thread thread = new Thread(runnable, "expedition-railway-height-" + ids.incrementAndGet());
            thread.setDaemon(true);
            return thread;
        });
    }

    @Inject(method = "buildQuadTree", at = @At("HEAD"), require = 1)
    private void expedition$resetFailure(double size, CallbackInfo ci) {
        expedition$sampleFailure = null;
    }

    @Redirect(method = "buildQuadTree", at = @At(value = "INVOKE",
        target = "Lcom/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler;buildNode(Lcom/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler$QuadTree;)V"),
        require = 1)
    private void expedition$enqueueRoot(AdaptiveHeightSampler ignored, @Coerce Object node) {
        executor.execute(() -> SamplerInternals.buildNode((AdaptiveHeightSampler)(Object)this, node));
    }

    @Redirect(method = "buildNode", at = @At(value = "INVOKE",
        target = "Lcom/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler;sampleNode(Lcom/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler$QuadTree;)V"),
        require = 1)
    private void expedition$captureFailure(AdaptiveHeightSampler ignored, @Coerce Object node) {
        if (expedition$sampleFailure != null) return;
        try {
            SamplerInternals.sampleNode((AdaptiveHeightSampler)(Object)this, node);
        } catch (Throwable failure) {
            expedition$sampleFailure = failure;
        }
    }

    @Redirect(method = "buildNode", at = @At(value = "INVOKE",
        target = "Lcom/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler;shouldSplit(Lcom/xkmxz/tongdarailway_for_forge/util/AdaptiveHeightSampler$QuadTree;)Z"),
        require = 1)
    private boolean expedition$stopAfterFailure(AdaptiveHeightSampler ignored, @Coerce Object node) {
        return expedition$sampleFailure == null && SamplerInternals.shouldSplit((AdaptiveHeightSampler)(Object)this, node);
    }

    @Inject(method = "buildQuadTree", at = @At("RETURN"), require = 1)
    private void expedition$propagateFailure(double size, CallbackInfo ci) {
        if (expedition$sampleFailure != null)
            throw new IllegalStateException("Tongda exact height sampling failed", expedition$sampleFailure);
    }
}
