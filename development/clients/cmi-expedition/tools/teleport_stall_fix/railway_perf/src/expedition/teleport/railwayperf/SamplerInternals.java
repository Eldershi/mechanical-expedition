package expedition.teleport.railwayperf;

import com.xkmxz.tongdarailway_for_forge.util.AdaptiveHeightSampler;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/** Exact-version bridge for Tongda's private QuadTree parameter type. */
public final class SamplerInternals {
    private static final Method BUILD = find("buildNode");
    private static final Method SAMPLE = find("sampleNode");
    private static final Method SPLIT = find("shouldSplit");
    private SamplerInternals() {}

    private static Method find(String name) {
        for (Method method : AdaptiveHeightSampler.class.getDeclaredMethods()) {
            if (method.getName().equals(name) && method.getParameterCount() == 1) {
                method.setAccessible(true);
                return method;
            }
        }
        throw new ExceptionInInitializerError("Tongda sampler method missing: " + name);
    }

    public static void buildNode(AdaptiveHeightSampler sampler, Object node) { invoke(BUILD, sampler, node); }
    public static void sampleNode(AdaptiveHeightSampler sampler, Object node) { invoke(SAMPLE, sampler, node); }
    public static boolean shouldSplit(AdaptiveHeightSampler sampler, Object node) {
        return (boolean) invoke(SPLIT, sampler, node);
    }

    private static Object invoke(Method method, AdaptiveHeightSampler sampler, Object node) {
        try {
            return method.invoke(sampler, node);
        } catch (InvocationTargetException e) {
            Throwable cause = e.getCause();
            if (cause instanceof Error error) throw error;
            if (cause instanceof RuntimeException error) throw error;
            throw new IllegalStateException("Tongda sampler invocation failed", cause);
        } catch (ReflectiveOperationException e) {
            throw new IllegalStateException("Tongda sampler bridge failed", e);
        }
    }
}
