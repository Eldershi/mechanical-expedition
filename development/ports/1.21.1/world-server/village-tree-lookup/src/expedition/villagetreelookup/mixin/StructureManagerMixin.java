package expedition.villagetreelookup.mixin;

import com.faboslav.villagesandpillages.common.tag.VillagesAndPillagesTags;
import expedition.villagetreelookup.TreeGenerationContext;
import net.minecraft.core.BlockPos;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.LevelAccessor;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = StructureManager.class, remap = false)
abstract class StructureManagerMixin {
    @Shadow @Final private LevelAccessor level;

    @Inject(method = "getStructureWithPieceAt(Lnet/minecraft/core/BlockPos;Lnet/minecraft/tags/TagKey;)"
        + "Lnet/minecraft/world/level/levelgen/structure/StructureStart;", at = @At("HEAD"), cancellable = true)
    private void expedition$useGenerationStructureManager(BlockPos pos, TagKey<Structure> tag,
            CallbackInfoReturnable<StructureStart> callback) {
        if (!VillagesAndPillagesTags.VILLAGE_WITCH.equals(tag)) {
            return;
        }
        var region = TreeGenerationContext.current();
        if (region != null && level == region.getLevel()) {
            var manager = ((StructureManager) (Object) this).forWorldGenRegion(region);
            callback.setReturnValue(manager.getStructureWithPieceAt(pos, tag));
        }
    }
}
