package expedition.teleport.railwayperf;

import com.xkmxz.tongdarailway_for_forge.util.AdaptiveHeightSampler;

import java.util.concurrent.ConcurrentHashMap;
import java.util.function.DoubleBinaryOperator;

/**
 * One sampler's exact block-height memo table. It never approximates heights.
 * The key repeats the upstream RoutePlanner lambda's integer arithmetic and
 * double-to-int conversion, including its behavior in negative regions.
 */
public final class ExactHeightMemoizer implements AdaptiveHeightSampler.HeightFunction {
    private final DoubleBinaryOperator delegate;
    private final int originX;
    private final int originZ;
    private final ConcurrentHashMap<Long, Double> heights = new ConcurrentHashMap<>(1024);

    public ExactHeightMemoizer(DoubleBinaryOperator delegate, int regionX, int regionZ, int chunkGroupSize) {
        this.delegate = delegate;
        this.originX = regionX * chunkGroupSize * 16;
        this.originZ = regionZ * chunkGroupSize * 16;
    }

    @Override
    public double getHeight(double x, double z) {
        int blockX = (int) (x * 8.0 + originX);
        int blockZ = (int) (z * 8.0 + originZ);
        long key = (blockX & 0xffffffffL) | ((long) blockZ << 32);
        return heights.computeIfAbsent(key, ignored -> delegate.applyAsDouble(x, z));
    }

    public int uniqueSamples() { return heights.size(); }
}
