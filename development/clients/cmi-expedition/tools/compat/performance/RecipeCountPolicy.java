package expedition.performance.policy;

/** Test copies can switch this off for a matched comparison. Defaults to on. */
public final class RecipeCountPolicy {
    public static volatile boolean enabled = true;
    private RecipeCountPolicy() {}
}
