package expedition.motionguard.mixin;

import expedition.motionguard.MotionPolicy;
import expedition.motionguard.diagnostics.DiagnosticsService;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.MoverType;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import net.minecraftforge.common.ForgeMod;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Runs before Alex's Caves collision injection; all non-player entities pass through. */
@Mixin(value = Entity.class, priority = 500, remap = false)
public abstract class PlayerMotionMixin {
    @Shadow private Vec3 f_19827_;
    @Unique private static final Logger expedition$motionLogger =
            LoggerFactory.getLogger("ExpeditionPlayerMotionGuard");
    @Unique private static final long expedition$warnInterval = 20_000_000_000L;
    @Unique private boolean expedition$hasWarned;
    @Unique private long expedition$lastWarning;

    // The DDD overload m_20334_ constructs a Vec3 and delegates to this setter.
    @Inject(method = "m_20256_(Lnet/minecraft/world/phys/Vec3;)V", at = @At("HEAD"),
            cancellable = true, require = 1, allow = 1, remap = false)
    private void expedition$checkMotionWrite(Vec3 motion, CallbackInfo ci) {
        if (!((Object) this instanceof ServerPlayer player)) return;
        MotionPolicy.Rejection rejection = expedition$inspect(player, motion);
        if (rejection == null) return;
        DiagnosticsService.unsafe(player,"setDeltaMovement",motion,rejection);
        expedition$report(player, "setDeltaMovement", motion, rejection);
        f_19827_ = Vec3.f_82478_;
        ci.cancel();
    }

    @Inject(method = "m_6478_(Lnet/minecraft/world/entity/MoverType;Lnet/minecraft/world/phys/Vec3;)V",
            at = @At("HEAD"), cancellable = true, require = 1, allow = 1, remap = false)
    private void expedition$checkMovement(MoverType type, Vec3 motion, CallbackInfo ci) {
        if (!((Object) this instanceof ServerPlayer player)) return;
        MotionPolicy.Rejection rejection = expedition$inspect(player, motion);
        if (rejection == null) return;
        DiagnosticsService.unsafe(player,"move/"+type,motion,rejection);
        expedition$report(player, "move/" + type, motion, rejection);
        f_19827_ = Vec3.f_82478_;
        ci.cancel();
    }

    // move can alter its argument through stuckSpeedMultiplier and edge handling.
    @Inject(method = "m_20272_(Lnet/minecraft/world/phys/Vec3;)Lnet/minecraft/world/phys/Vec3;",
            at = @At("HEAD"), cancellable = true, require = 1, allow = 1, remap = false)
    private void expedition$checkCollision(Vec3 motion, CallbackInfoReturnable<Vec3> cir) {
        if (!((Object) this instanceof ServerPlayer player)) return;
        MotionPolicy.Rejection rejection = expedition$inspect(player, motion);
        if (rejection == null) return;
        DiagnosticsService.unsafe(player,"collide",motion,rejection);
        expedition$report(player, "collide", motion, rejection);
        f_19827_ = Vec3.f_82478_;
        cir.setReturnValue(Vec3.f_82478_);
    }

    @Unique
    private static MotionPolicy.Rejection expedition$inspect(ServerPlayer player, Vec3 motion) {
        AABB box = player.m_20191_();
        return MotionPolicy.inspect(motion.f_82479_, motion.f_82480_, motion.f_82481_,
                box.f_82288_, box.f_82289_, box.f_82290_,
                box.f_82291_, box.f_82292_, box.f_82293_);
    }

    @Unique
    private void expedition$report(ServerPlayer player, String source, Vec3 motion,
                                   MotionPolicy.Rejection rejection) {
        long now = System.nanoTime();
        if (expedition$hasWarned && now - expedition$lastWarning < expedition$warnInterval) return;
        expedition$hasWarned = true;
        expedition$lastWarning = now;
        // Only read already-present state; never load chunks while handling invalid movement.
        double stepAddition = player.m_21133_(ForgeMod.STEP_HEIGHT_ADDITION.get());
        String message = "Rejected unsafe player collision query"
                + " source=" + source + " entityId=" + player.m_19879_()
                + " dimension=" + player.m_9236_().m_46472_().m_135782_()
                + " reason=" + rejection.reason()
                + " motion=" + motion
                + " currentDelta=" + player.m_20184_()
                + " position=" + player.m_20182_()
                + " originalBox=" + rejection.original()
                + " sweptBox=" + rejection.swept()
                + " sectionsXYZ=" + rejection.sectionsX() + "," + rejection.sectionsY() + "," + rejection.sectionsZ()
                + " sectionCountCapped=" + rejection.sectionCountCapped()
                + " sectionBudget=" + MotionPolicy.SECTION_BUDGET
                + " baseStepHeight=" + player.m_274421_()
                + " stepHeightAttribute=" + stepAddition;
        expedition$motionLogger.warn(message, new Throwable("Unsafe movement caller"));
    }
}
