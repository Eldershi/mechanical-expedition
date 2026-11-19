package expedition.space.cooling;

import com.simibubi.create.content.processing.basin.BasinBlockEntity;
import com.simibubi.create.content.processing.burner.BlazeBurnerBlock.HeatLevel;
import com.yision.fluidlogistics.content.processing.cooling.CoolingRecipe;
import com.yision.fluidlogistics.content.processing.snowGolemFreezer.SnowGolemFreezerBlockEntity;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.ty.createcraftedbeginning.content.breezes.breezecooler.BreezeCoolerBlock.FrostLevel;
import net.ty.createcraftedbeginning.content.breezes.breezecooler.BreezeCoolerBlockEntity;
import net.ty.createcraftedbeginning.platform.SubLevelBridge;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

public final class CoolingSources {
    private CoolingSources() {}

    public static boolean isCooler(BlockEntity entity) {
        return entity instanceof SnowGolemFreezerBlockEntity || entity instanceof BreezeCoolerBlockEntity;
    }

    public static boolean activeSnowGolem(BlockEntity entity) {
        return entity instanceof SnowGolemFreezerBlockEntity freezer
            && freezer.getHeatLevelFromBlock().isAtLeast(HeatLevel.FADING);
    }

    public static boolean activeBreeze(BlockEntity entity) {
        return entity instanceof BreezeCoolerBlockEntity cooler && cooler.getFrostLevel() == FrostLevel.CHILLED;
    }

    public static boolean hasSnowGolemBelow(BasinBlockEntity basin) {
        var level = basin.getLevel();
        var pos = basin.getBlockPos();
        return level != null && SubLevelBridge.findAt(level, pos, pos.below(),
            candidate -> activeSnowGolem(level.getBlockEntity(candidate)) ? Boolean.TRUE : null) != null;
    }

    public static void requireBasinCooling(BasinBlockEntity basin, Recipe<?> recipe, CallbackInfoReturnable<Boolean> result) {
        if (!(recipe instanceof CoolingRecipe)) return;
        var level = basin.getLevel();
        var pos = basin.getBlockPos();
        if (level != null && (activeSnowGolem(level.getBlockEntity(pos.below()))
                || SubLevelBridge.findAt(level, pos, pos.below(),
                    candidate -> activeBreeze(level.getBlockEntity(candidate)) ? Boolean.TRUE : null) != null)) return;
        result.setReturnValue(false);
    }
}
