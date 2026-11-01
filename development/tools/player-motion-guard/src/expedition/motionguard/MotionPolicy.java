package expedition.motionguard;

/** Bounds the cost and representability of a single player collision query. */
public final class MotionPolicy {
    public static final double WORLD_LIMIT = 30_000_000.0;
    public static final long SECTION_BUDGET = 4096L;
    private static final double EPSILON = 1.0e-7;

    private MotionPolicy() {}

    public record Box(double minX, double minY, double minZ,
                      double maxX, double maxY, double maxZ) {}

    public record Rejection(String reason, Box original, Box swept,
                            long sectionsX, long sectionsY, long sectionsZ,
                            long sectionCountCapped) {}

    /** Returns null for an ordinary query; does not change speed or coordinates. */
    public static Rejection inspect(double dx, double dy, double dz,
                                    double minX, double minY, double minZ,
                                    double maxX, double maxY, double maxZ) {
        double sweptMinX = minX + (dx < 0 ? dx : 0);
        double sweptMinY = minY + (dy < 0 ? dy : 0);
        double sweptMinZ = minZ + (dz < 0 ? dz : 0);
        double sweptMaxX = maxX + (dx > 0 ? dx : 0);
        double sweptMaxY = maxY + (dy > 0 ? dy : 0);
        double sweptMaxZ = maxZ + (dz > 0 ? dz : 0);
        String reason = null;
        long sectionsX = -1, sectionsY = -1, sectionsZ = -1, count = -1;
        if (!finite(dx, dy, dz)) reason = "non_finite_motion";
        else if (!finite(minX, minY, minZ) || !finite(maxX, maxY, maxZ))
            reason = "non_finite_original_box";
        else if (minX > maxX || minY > maxY || minZ > maxZ)
            reason = "inverted_original_box";
        else if (!finite(sweptMinX, sweptMinY, sweptMinZ)
                || !finite(sweptMaxX, sweptMaxY, sweptMaxZ))
            reason = "non_finite_swept_box";
        else if (sweptMinX < -WORLD_LIMIT || sweptMaxX > WORLD_LIMIT
                || sweptMinZ < -WORLD_LIMIT || sweptMaxZ > WORLD_LIMIT)
            reason = "outside_horizontal_world_range";
        else if (Math.floor(sweptMinY - 4.0 - EPSILON) < Integer.MIN_VALUE + 1.0
                || Math.floor(sweptMaxY + 2.0 + EPSILON) > Integer.MAX_VALUE - 1.0)
            reason = "unsafe_vertical_integer_range";
        else {
            // A conservative union of entity queries (XZ +/-2, Y -4/+0)
            // and BlockCollisions' floor(bounds +/- epsilon) +/-1 cursors.
            sectionsX = span(sweptMinX - 2.0 - EPSILON, sweptMaxX + 2.0 + EPSILON);
            sectionsY = span(sweptMinY - 4.0 - EPSILON, sweptMaxY + 2.0 + EPSILON);
            sectionsZ = span(sweptMinZ - 2.0 - EPSILON, sweptMaxZ + 2.0 + EPSILON);
            count = cappedProduct(cappedProduct(sectionsX, sectionsY), sectionsZ);
            if (count >= SECTION_BUDGET) reason = "collision_section_budget";
        }
        if (reason == null) return null;
        return new Rejection(reason, new Box(minX, minY, minZ, maxX, maxY, maxZ),
                new Box(sweptMinX, sweptMinY, sweptMinZ,
                        sweptMaxX, sweptMaxY, sweptMaxZ), sectionsX, sectionsY, sectionsZ, count);
    }

    private static long span(double minimum, double maximum) {
        return (long) Math.floor(maximum / 16.0) - (long) Math.floor(minimum / 16.0) + 1;
    }

    private static long cappedProduct(long first, long second) {
        // Saturate at the budget without ever evaluating an overflowing product.
        return first > (SECTION_BUDGET - 1) / second ? SECTION_BUDGET : first * second;
    }

    private static boolean finite(double x, double y, double z) {
        return Double.isFinite(x) && Double.isFinite(y) && Double.isFinite(z);
    }
}
