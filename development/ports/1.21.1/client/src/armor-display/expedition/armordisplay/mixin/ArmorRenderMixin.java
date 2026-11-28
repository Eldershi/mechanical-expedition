package expedition.armordisplay.mixin;

import java.util.Map;

import expedition.armordisplay.ArmorDisplayIndex;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.chunk.LevelChunk;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "net.mcreator.protectionpixel.procedures.ArmorrenderProcedure", remap = false)
abstract class ArmorRenderMixin {
    @Redirect(method = "execute(Lnet/neoforged/bus/api/Event;Lnet/minecraft/world/level/LevelAccessor;)V",
        at = @At(value = "INVOKE", target = "Lnet/minecraft/world/level/chunk/LevelChunk;getBlockEntities()Ljava/util/Map;"))
    private static Map<BlockPos, BlockEntity> expedition$armorDisplaysOnly(LevelChunk chunk) {
        return ((ArmorDisplayIndex) chunk).expedition$armorDisplays();
    }
}
