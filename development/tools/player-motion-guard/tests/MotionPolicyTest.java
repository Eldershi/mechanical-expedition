import expedition.motionguard.MotionPolicy;

public final class MotionPolicyTest {
    private static MotionPolicy.Rejection inspect(double x, double y, double z) {
        return MotionPolicy.inspect(x,y,z,99.7,64,99.7,100.3,65.8,100.3);
    }
    private static void check(boolean value, String name) {
        if (!value) throw new AssertionError(name);
    }
    public static void main(String[] args) {
        check(inspect(.2,-.08,.2)==null,"walking");
        check(inspect(20,30,-20)==null,"fast flight");
        check(inspect(10_000,0,0)==null,"long narrow finite query is not a fixed speed cap");
        check(inspect(Double.NaN,0,0).reason().equals("non_finite_motion"),"NaN");
        check(inspect(Double.NEGATIVE_INFINITY,0,0)!=null,"infinity");
        check(inspect(1e300,0,0).reason().equals("outside_horizontal_world_range"),"finite extreme");
        check(inspect(2_000,0,2_000).reason().equals("collision_section_budget"),"finite query cost");
        check(MotionPolicy.inspect(0,0,0,0,0,0,Double.NaN,2,1)!=null,"bad original box");
        check(MotionPolicy.inspect(0,0,0,1,0,0,0,2,1).reason().equals("inverted_original_box"),"inverted box");
        check(MotionPolicy.inspect(0,0,0,30_000_001,0,0,30_000_002,2,1)!=null,"bad original world position");
        check(MotionPolicy.inspect(0,0,0,2.1,4.1,2.1,237.9,238,238)==null,"below 3D section budget");
        var exact=MotionPolicy.inspect(0,0,0,2.1,4.1,2.1,238,238,238);
        check(exact!=null && exact.sectionCountCapped()==4096,"exact 3D section budget boundary");
        check(inspect(0,1e300,0).reason().equals("unsafe_vertical_integer_range"),"huge finite upward velocity");
        check(inspect(0,-1e300,0).reason().equals("unsafe_vertical_integer_range"),"huge finite downward velocity");
        check(inspect(0,1e7,0).reason().equals("collision_section_budget"),"representable but costly vertical query");
        check(MotionPolicy.inspect(0,0.5,0,99.7,1e7,99.7,100.3,1e7+1.8,100.3)==null,"high Y small motion");
        check(MotionPolicy.inspect(0,0,0,99.7,1e300,99.7,100.3,1e300,100.3)!=null,"huge original bbox Y");
        check(MotionPolicy.inspect(0,0,0,-3e7,64,-3e7,3e7,66,3e7).sectionCountCapped()==4096,"product saturates safely");
        check(MotionPolicy.inspect(0,0,0,29_999_990,64,99.7,29_999_991,66,100.3)==null,"small query near world boundary");
        check(inspect(0,Double.POSITIVE_INFINITY,0)!=null,"positive infinity");
        System.out.println("MOTION_POLICY_OK: 20 finite, invalid, world-range, vertical and 3D scan-budget boundaries");
    }
}
