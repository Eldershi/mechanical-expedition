package expedition.armordisplay;

import java.util.Map;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;

public interface ArmorDisplayIndex {
    Map<BlockPos, BlockEntity> expedition$armorDisplays();
}
