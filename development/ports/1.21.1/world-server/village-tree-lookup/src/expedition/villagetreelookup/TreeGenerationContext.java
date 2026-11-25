package expedition.villagetreelookup;

import net.minecraft.server.level.WorldGenRegion;

public final class TreeGenerationContext {
    private static final ThreadLocal<WorldGenRegion> REGION = new ThreadLocal<>();

    private TreeGenerationContext() {}

    public static WorldGenRegion current() {
        return REGION.get();
    }

    public static void set(WorldGenRegion region) {
        if (region == null) {
            REGION.remove();
        } else {
            REGION.set(region);
        }
    }
}
