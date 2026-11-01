package expedition.motionprobe;

import java.util.UUID;
import com.mojang.authlib.GameProfile;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.animal.Pig;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.Blocks;
import net.minecraftforge.common.MinecraftForge;
import net.minecraftforge.common.util.FakePlayer;
import net.minecraftforge.common.util.FakePlayerFactory;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.fml.common.Mod;

/** Disposable server fixture; never installed on the shared server. */
@Mod("expedition_motion_probe")
public final class MotionProbe {
    public MotionProbe() {
        MinecraftForge.EVENT_BUS.addListener(this::started);
    }

    private void check(boolean value, String label) {
        if (!value) throw new AssertionError(label);
        System.out.println("MOTION_PROBE_OK " + label);
    }

    private void zero(FakePlayer player, String label) {
        check(player.m_20184_().m_82556_() == 0.0, label);
    }

    private void started(ServerStartedEvent event) {
        try {
            ServerLevel level = event.getServer().m_129783_();
            FakePlayer player = FakePlayerFactory.get(level,
                new GameProfile(UUID.fromString("12121212-3434-5656-7878-909090909090"), "MotionProbe"));
            for (int x = -2; x <= 6; x++) {
                for (int z = -2; z <= 2; z++) {
                    level.m_46597_(new BlockPos(x, 3, z), Blocks.f_50069_.m_49966_());
                }
            }
            player.m_6034_(0.5, 4.0, 0.5);
            AABB validBox = player.m_20191_();
            Vec3 normal = new Vec3(0.15, 0.42, -0.2);
            player.m_20256_(normal);
            check(player.m_20184_().equals(normal), "ordinary_motion_preserved");
            Vec3 flight = new Vec3(8.0, 3.0, -8.0);
            player.m_20256_(flight);
            check(player.m_20184_().equals(flight), "fast_flight_motion_preserved");
            player.m_20334_(Double.NaN, 0.0, 0.0);
            zero(player, "double_setter_nan_rejected");
            player.m_20256_(new Vec3(0.0, Double.POSITIVE_INFINITY, 0.0));
            zero(player, "positive_infinity_rejected");
            player.m_20256_(new Vec3(0.0, 0.0, Double.NEGATIVE_INFINITY));
            zero(player, "negative_infinity_rejected");
            player.m_20256_(new Vec3(1.0e10, 0.0, 0.0));
            zero(player, "world_overflow_velocity_rejected");
            player.m_20256_(new Vec3(100000.0, 0.0, 100000.0));
            zero(player, "finite_excessive_sweep_rejected");
            player.m_20256_(new Vec3(0.0, 1.0e300, 0.0));
            zero(player, "finite_extreme_vertical_motion_rejected");
            double beforeX = player.m_20185_(), beforeY = player.m_20186_(), beforeZ = player.m_20189_();
            player.m_6478_(MoverType.SELF, new Vec3(Double.NaN, 0.0, 0.0));
            check(player.m_20185_() == beforeX && player.m_20186_() == beforeY && player.m_20189_() == beforeZ,
                "direct_move_nan_cancelled_before_collision");
            player.m_6478_(MoverType.SELF, new Vec3(33554432.0, 0.0, 0.0));
            check(player.m_20185_() == beforeX && player.m_20189_() == beforeZ,
                "direct_move_section_overflow_cancelled_before_collision");
            player.m_6478_(MoverType.SELF, new Vec3(100000.0, 0.0, 100000.0));
            check(player.m_20185_() == beforeX && player.m_20189_() == beforeZ,
                "direct_move_finite_scan_budget_cancelled");
            java.lang.reflect.Method collide = net.minecraft.world.entity.Entity.class.getDeclaredMethod("m_20272_", Vec3.class);
            collide.setAccessible(true);
            Vec3 rejectedCollision = (Vec3) collide.invoke(player, new Vec3(Double.NaN, 0.0, 0.0));
            check(rejectedCollision.m_82556_() == 0.0, "final_collision_guard_precedes_alexscaves");
            player.m_20011_(new AABB(Double.NaN, 0.0, 0.0, Double.NaN, 2.0, 1.0));
            player.m_6478_(MoverType.SELF, new Vec3(0.1, 0.0, 0.0));
            check(player.m_20185_() == beforeX && player.m_20189_() == beforeZ, "invalid_original_box_cancelled");
            player.m_20011_(validBox);
            player.m_6034_(3000.5, 80.0, 2500.5);
            player.m_20256_(normal);
            check(player.m_20185_() == 3000.5 && player.m_20189_() == 2500.5 && player.m_20184_().equals(normal),
                "distant_position_change_preserved");
            player.m_6034_(0.5, 4.0, 0.5);
            player.m_20256_(Vec3.f_82478_);
            player.m_6478_(MoverType.SELF, new Vec3(0.1, 0.0, 0.0));
            check(Math.abs(player.m_20185_() - 0.6) < 0.001, "ordinary_collision_move_preserved");
            for (int y = 4; y <= 6; y++) {
                level.m_46597_(new BlockPos(2, y, 0), Blocks.f_50069_.m_49966_());
            }
            player.m_6034_(0.5, 4.0, 0.5);
            player.m_6478_(MoverType.SELF, new Vec3(2.0, 0.0, 0.0));
            check(player.m_20185_() > 1.69 && player.m_20185_() < 1.71, "solid_wall_collision_preserved");
            player.m_6034_(4.5, 8.0, 0.5);
            player.m_6478_(MoverType.SELF, new Vec3(0.0, -10.0, 0.0));
            check(Math.abs(player.m_20186_() - 4.0) < 0.001, "floor_landing_collision_preserved");
            Pig pig = EntityType.f_20510_.m_20615_(level);
            if (pig == null) throw new AssertionError("pig factory");
            pig.m_20256_(new Vec3(Double.NaN, 0.0, 0.0));
            check(Double.isNaN(pig.m_20184_().f_82479_), "non_player_motion_unchanged");
            System.out.println("MOTION_PROBE_PASSED");
        } catch (Throwable problem) {
            System.out.println("MOTION_PROBE_FAILED");
            problem.printStackTrace();
        }
    }
}
