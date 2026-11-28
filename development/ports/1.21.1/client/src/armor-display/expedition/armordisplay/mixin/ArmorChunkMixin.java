package expedition.armordisplay.mixin;

import java.util.LinkedHashMap;
import java.util.Map;

import expedition.armordisplay.ArmorDisplayIndex;
import net.mcreator.protectionpixel.init.ProtectionPixelModBlocks;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.chunk.LevelChunk;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(LevelChunk.class)
abstract class ArmorChunkMixin implements ArmorDisplayIndex {
    @Shadow public abstract Map<BlockPos, BlockEntity> getBlockEntities();

    @Unique private Map<BlockPos, BlockEntity> expedition$armorDisplays;

    @Override
    public Map<BlockPos, BlockEntity> expedition$armorDisplays() {
        if (expedition$armorDisplays == null) {
            var displays = new LinkedHashMap<BlockPos, BlockEntity>();
            for (var entry : getBlockEntities().entrySet()) {
                if (expedition$isArmorDisplay(entry.getValue())) {
                    displays.put(entry.getKey(), entry.getValue());
                }
            }
            expedition$armorDisplays = displays.isEmpty() ? Map.of() : displays;
        }
        return expedition$armorDisplays;
    }

    @Inject(method = "setBlockEntity", at = @At("RETURN"))
    private void expedition$refreshChangedDisplay(BlockEntity entity, CallbackInfo callback) {
        if (expedition$armorDisplays != null && (expedition$isArmorDisplay(entity)
                || expedition$armorDisplays.containsKey(entity.getBlockPos()))) {
            expedition$armorDisplays = null;
        }
    }

    @Inject(method = "removeBlockEntity", at = @At("RETURN"))
    private void expedition$refreshRemovedDisplay(BlockPos pos, CallbackInfo callback) {
        if (expedition$armorDisplays != null && expedition$armorDisplays.containsKey(pos)) {
            expedition$armorDisplays = null;
        }
    }

    @Inject(method = "clearAllBlockEntities", at = @At("RETURN"))
    private void expedition$clearDisplays(CallbackInfo callback) {
        expedition$armorDisplays = null;
    }

    @Unique
    private static boolean expedition$isArmorDisplay(BlockEntity entity) {
        var block = entity.getBlockState().getBlock();
        return block == ProtectionPixelModBlocks.ARMORHANGER.get()
            || block == ProtectionPixelModBlocks.ARMORLOADPLATFORM.get()
            || block == ProtectionPixelModBlocks.FOLDEDSTEAMECTOSKELETON.get();
    }
}
