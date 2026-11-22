package expedition.alloyfurnace.mixin;

import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import expedition.alloyfurnace.AlloyFurnace;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(MBDMultiblockMachine.class)
abstract class HydraulicPressMotionMixin {
    @Inject(method = "serverTick", at = @At("TAIL"), remap = false)
    private void expedition$syncPressCycle(CallbackInfo callback) {
        var press = (MBDMultiblockMachine) (Object) this;
        if (!AlloyFurnace.isHydraulicPress(press) || press.getOffsetTimer() % 4 != 0) return;
        var logic = press.getRecipeLogic();
        var recipe = logic.getLastOriginRecipe();
        var current = press.getCustomData();
        if (!press.isFormedValid() || !logic.isWorking() || recipe == null) {
            if (current.getInt("pressMode") != 0) {
                var update = current.copy();
                update.putInt("pressMode", 0);
                press.setCustomData(update);
            }
            return;
        }
        var level = press.getLevel();
        if (level == null) return;
        long start = level.getGameTime() - logic.getProgress();
        int mode = recipe.getPath().endsWith("_ingot") ? 2 : 1;
        int duration = logic.getDuration();
        if (current.getInt("pressMode") == mode && current.getInt("pressDuration") == duration
                && Math.abs(current.getLong("pressStart") - start) < 4) return;
        var update = current.copy();
        update.putInt("pressMode", mode);
        update.putLong("pressStart", start);
        update.putInt("pressDuration", duration);
        press.setCustomData(update);
    }
}
