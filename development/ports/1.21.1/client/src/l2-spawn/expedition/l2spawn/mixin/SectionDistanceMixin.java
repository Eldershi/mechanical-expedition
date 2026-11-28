package expedition.l2spawn.mixin;

import dev.xkmc.l2hostility.content.capability.chunk.SectionDifficulty;
import dev.xkmc.l2hostility.content.logic.MobDifficultyCollector;
import net.minecraft.core.BlockPos;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(value = SectionDifficulty.class, remap = false)
abstract class SectionDistanceMixin {
    @Redirect(
        method = "modifyInstanceInternal",
        at = @At(value = "INVOKE", target = "Ljava/lang/Math;sqrt(D)D"),
        require = 1, allow = 1
    )
    private double expedition$mobDistance(double originalSquared, Level level, BlockPos pos,
                                          MobDifficultyCollector collector) {
        return expedition$distanceFromSpawn(originalSquared, level, pos);
    }

    @Redirect(
        method = "getSectionDifficultyDetail",
        at = @At(value = "INVOKE", target = "Ljava/lang/Math;sqrt(D)D"),
        require = 1, allow = 1
    )
    private double expedition$displayedDistance(double originalSquared, Player player) {
        return expedition$distanceFromSpawn(originalSquared, player.level(), player.blockPosition());
    }

    @Unique
    private static double expedition$distanceFromSpawn(double originalSquared, Level level, BlockPos pos) {
        if (!level.dimension().equals(Level.OVERWORLD)) {
            return Math.sqrt(originalSquared);
        }
        BlockPos spawn = level.getSharedSpawnPos();
        double x = (double) pos.getX() - spawn.getX();
        double z = (double) pos.getZ() - spawn.getZ();
        return Math.sqrt(x * x + z * z);
    }
}
