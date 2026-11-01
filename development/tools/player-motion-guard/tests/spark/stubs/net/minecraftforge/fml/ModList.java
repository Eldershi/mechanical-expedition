package net.minecraftforge.fml;

/** Test-only Forge boundary; the real production class is not replaced in a game. */
public final class ModList {
    private static final ModList INSTANCE = new ModList();
    public static ModList get() { return INSTANCE; }
    public boolean isLoaded(String id) { return id.equals("spark"); }
}
