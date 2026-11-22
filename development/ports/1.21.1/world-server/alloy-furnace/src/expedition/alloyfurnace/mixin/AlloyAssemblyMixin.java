package expedition.alloyfurnace.mixin;

import com.lowdragmc.mbd2.api.block.ProxyPartBlock;
import com.lowdragmc.mbd2.api.blockentity.ProxyPartBlockEntity;
import com.lowdragmc.mbd2.common.machine.MBDMachine;
import com.lowdragmc.mbd2.common.machine.MBDMultiblockMachine;
import expedition.alloyfurnace.AlloyFurnace;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Block;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(MBDMultiblockMachine.class)
abstract class AlloyAssemblyMixin {
    @Redirect(method = "onStructureFormed", at = @At(value = "INVOKE",
        target = "Lcom/lowdragmc/mbd2/api/block/ProxyPartBlock;replaceOriginalBlock(Lnet/minecraft/core/BlockPos;Lnet/minecraft/world/level/Level;Lnet/minecraft/core/BlockPos;I)V"),
        remap = false)
    private void expedition$preserveAlloyParts(BlockPos controller, Level level, BlockPos pos, int predicate) {
        if (!AlloyFurnace.isController((MBDMachine) (Object) this)) {
            ProxyPartBlock.replaceOriginalBlock(controller, level, pos, predicate);
            return;
        }
        var original = level.getBlockState(pos);
        var originalEntity = level.getBlockEntity(pos);
        var data = originalEntity == null ? null : originalEntity.saveWithFullMetadata(level.registryAccess());
        // Install the saved state before any nearby pipe or funnel can query the new port.
        level.setBlock(pos, ProxyPartBlock.BLOCK.defaultBlockState(), Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE);
        if (level.getBlockEntity(pos) instanceof ProxyPartBlockEntity proxy) {
            proxy.setOriginalData(original, data, controller, predicate);
            proxy.setChanged();
        }
    }
}
