package expedition.twilight.mixin;

import expedition.twilight.TwilightLandmarks;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.LevelReader;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;
import twilightforest.item.MagicMapItem;
import twilightforest.util.landmarks.LegacyLandmarkPlacements;

@Mixin(value = MagicMapItem.class, remap = false)
public abstract class MagicMapMixin {
    @Redirect(method = "update", at = @At(value = "INVOKE", target =
        "Ltwilightforest/util/landmarks/LegacyLandmarkPlacements;pickLandmarkAtBlock(IILnet/minecraft/world/level/LevelReader;)Lnet/minecraft/resources/ResourceKey;"))
    private ResourceKey<Structure> expedition$visibleLandmark(int x, int z, LevelReader reader) {
        var id = LegacyLandmarkPlacements.pickLandmarkAtBlock(x, z, reader);
        if (id != null && reader instanceof ServerLevel level
                && !TwilightLandmarks.allows(id, level.getSeed(), x >> 4, z >> 4)
                && !TwilightLandmarks.hasExistingStart(level, id, x >> 4, z >> 4)) {
            return ResourceKey.create(Registries.STRUCTURE, ResourceLocation.parse("expedition_worldgen_compat:filtered_landmark"));
        }
        return id;
    }
}
