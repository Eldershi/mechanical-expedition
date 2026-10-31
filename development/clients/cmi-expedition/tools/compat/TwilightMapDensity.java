package expedition.worldgen.mixin;

import expedition.worldgen.BossDensityPolicy;

import net.minecraft.core.BlockPos;
import net.minecraft.world.level.WorldGenLevel;
import twilightforest.init.TFLandmark;
import twilightforest.util.LegacyLandmarkPlacements;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** New and previously stored magic-map markers follow the same sparse boss filter. */
@Mixin(targets="twilightforest.item.MagicMapItem",remap=false)
public abstract class TwilightMapDensity {
    @Redirect(method="m_42893_",at=@At(value="INVOKE",target="Ltwilightforest/util/LegacyLandmarkPlacements;pickLandmarkAtBlock(IILnet/minecraft/world/level/WorldGenLevel;)Ltwilightforest/init/TFLandmark;",remap=false),remap=false)
    private TFLandmark expedition$mapLandmark(int blockX,int blockZ,WorldGenLevel level) {
        TFLandmark landmark=LegacyLandmarkPlacements.pickLandmarkAtBlock(blockX,blockZ,level);
        String path=switch(landmark.name) {
            case "ice_tower" -> "aurora_palace";
            case "yeti_lairs" -> "yeti_cave";
            case "troll_lairs" -> "troll_cave";
            default -> landmark.name;
        };
        BlockPos center=LegacyLandmarkPlacements.getNearestCenterXZ(blockX>>4,blockZ>>4);
        return BossDensityPolicy.allowsId("twilightforest:"+path,level.m_7328_(),center.m_123341_()>>4,center.m_123343_()>>4)
            ?landmark:TFLandmark.NOTHING;
    }
}
