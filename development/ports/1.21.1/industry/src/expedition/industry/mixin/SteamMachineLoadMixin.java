package expedition.industry.mixin;

import expedition.industry.SteamMachineMigration;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.level.block.entity.BlockEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Mixin(BlockEntity.class)
public abstract class SteamMachineLoadMixin {
    @ModifyVariable(method = "loadStatic", at = @At("HEAD"), argsOnly = true)
    private static CompoundTag expedition$migrateSteamMachine(CompoundTag data) {
        return SteamMachineMigration.migrate(data);
    }
}
