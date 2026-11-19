package expedition.space.mixin;

import com.simibubi.create.content.kinetics.fan.AirCurrent;
import com.simibubi.create.content.kinetics.fan.IAirCurrentSource;
import com.simibubi.create.content.kinetics.fan.processing.FanProcessingType;
import expedition.space.cooling.CoolingFanProcessing;
import expedition.space.cooling.CoolingSources;
import java.util.HashMap;
import java.util.Map;
import net.minecraft.core.BlockPos;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = AirCurrent.class, remap = false)
abstract class AirCurrentCoolingMixin {
    @Shadow @Final public IAirCurrentSource source;
    @Shadow public abstract void rebuild();
    @Shadow public abstract void findAffectedHandlers();

    @Unique private final Map<BlockPos, FanProcessingType> expedition$coolers = new HashMap<>();

    @Inject(method = "rebuild", at = @At("HEAD"))
    private void expedition$clearCoolers(CallbackInfo ci) {
        expedition$coolers.clear();
    }

    @Redirect(method = {"rebuild", "findAffectedHandlers"}, at = @At(value = "INVOKE",
        target = "Lcom/simibubi/create/content/kinetics/fan/processing/FanProcessingType;getAt(Lnet/minecraft/world/level/Level;Lnet/minecraft/core/BlockPos;)Lcom/simibubi/create/content/kinetics/fan/processing/FanProcessingType;"))
    private FanProcessingType expedition$rememberCooler(Level level, BlockPos pos) {
        var sourceEntity = level.getBlockEntity(pos);
        var type = CoolingFanProcessing.forAirCurrent(sourceEntity, FanProcessingType.getAt(level, pos));
        if (CoolingSources.isCooler(sourceEntity)) expedition$coolers.put(pos.immutable(), type);
        return type;
    }

    @Inject(method = "tick", at = @At("HEAD"))
    private void expedition$refreshCooling(CallbackInfo ci) {
        // Create caches airflow segments, so refresh them before processing when a cooler stops or starts.
        if (expedition$coolers.isEmpty() || source.isSourceRemoved()) return;
        var level = source.getAirCurrentWorld();
        if (level == null || level.isClientSide()) return;
        for (var cooler : expedition$coolers.entrySet()) {
            var pos = cooler.getKey();
            var current = CoolingFanProcessing.forAirCurrent(level.getBlockEntity(pos), FanProcessingType.getAt(level, pos));
            if (current != cooler.getValue()) {
                rebuild();
                findAffectedHandlers();
                return;
            }
        }
    }
}
