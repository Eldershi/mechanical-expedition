package expedition.armordisplay.mixin;

import expedition.armordisplay.NearbyArmorDisplays;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.chunk.LevelChunk;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(LevelChunk.class)
abstract class ArmorChunkMixin {
    @Shadow public abstract Level getLevel();

    @Inject(method = "setBlockEntity", at = @At("RETURN"))
    private void expedition$refreshNewDisplay(BlockEntity entity, CallbackInfo callback) {
        if (getLevel().isClientSide && NearbyArmorDisplays.isArmorDisplay(entity)) {
            NearbyArmorDisplays.invalidate();
        }
    }

    @Inject(method = "replaceWithPacketData", at = @At("RETURN"))
    private void expedition$refreshChunkPacket(CallbackInfo callback) {
        if (getLevel().isClientSide) NearbyArmorDisplays.invalidate();
    }
}
