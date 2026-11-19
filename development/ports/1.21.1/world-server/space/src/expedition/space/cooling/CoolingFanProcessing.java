package expedition.space.cooling;

import com.simibubi.create.api.registry.CreateBuiltInRegistries;
import com.simibubi.create.content.kinetics.fan.processing.FanProcessingType;
import java.util.List;
import java.util.function.Supplier;
import net.minecraft.core.BlockPos;
import net.minecraft.util.RandomSource;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.phys.Vec3;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.neoforge.registries.DeferredRegister;
import net.ty.createcraftedbeginning.registry.CCBFanProcessingTypes;
import plus.dragons.createdragonsplus.common.registry.CDPFanProcessingTypes;

public final class CoolingFanProcessing implements FanProcessingType {
    private static final DeferredRegister<FanProcessingType> TYPES =
        DeferredRegister.create(CreateBuiltInRegistries.FAN_PROCESSING_TYPE.key(), "expedition_space");
    private static final Supplier<CoolingFanProcessing> SNOW = TYPES.register("active_snow_golem_freezing",
        () -> new CoolingFanProcessing(CDPFanProcessingTypes.FREEZING, CCBFanProcessingTypes.CHILLING, 600));
    private static final Supplier<CoolingFanProcessing> BREEZE = TYPES.register("active_breeze_chilling",
        () -> new CoolingFanProcessing(CCBFanProcessingTypes.CHILLING, CDPFanProcessingTypes.FREEZING, 550));

    private final Supplier<? extends FanProcessingType> primary;
    private final Supplier<? extends FanProcessingType> fallback;
    private final int priority;

    private CoolingFanProcessing(Supplier<? extends FanProcessingType> primary,
                                 Supplier<? extends FanProcessingType> fallback, int priority) {
        this.primary = primary;
        this.fallback = fallback;
        this.priority = priority;
    }

    public static void register(IEventBus bus) {
        TYPES.register(bus);
    }

    public static FanProcessingType forAirCurrent(BlockEntity source, FanProcessingType nativeType) {
        if (CoolingSources.activeSnowGolem(source) && nativeType == CDPFanProcessingTypes.FREEZING.get()) {
            return SNOW.get();
        }
        if (CoolingSources.activeBreeze(source) && nativeType == CCBFanProcessingTypes.CHILLING.get()) {
            return BREEZE.get();
        }
        return nativeType;
    }

    public static FanProcessingType nativeType(FanProcessingType type) {
        return type instanceof CoolingFanProcessing cooling ? cooling.primary.get() : type;
    }

    @Override
    public boolean isValidAt(Level level, BlockPos pos) {
        // AirCurrent selects these types after Create resolves its ordinary catalyst priority.
        return false;
    }

    @Override public int getPriority() { return priority; }

    @Override
    public boolean canProcess(ItemStack stack, Level level) {
        return primary.get().canProcess(stack, level) || fallback.get().canProcess(stack, level);
    }

    @Override
    public List<ItemStack> process(ItemStack stack, Level level) {
        var outputs = primary.get().process(stack, level);
        if (outputs != null) return outputs;
        var alternate = fallback.get();
        return alternate.canProcess(stack, level) ? alternate.process(stack, level) : null;
    }

    @Override public void spawnProcessingParticles(Level level, Vec3 pos) {
        primary.get().spawnProcessingParticles(level, pos);
    }

    @Override public void morphAirFlow(AirFlowParticleAccess particle, RandomSource random) {
        primary.get().morphAirFlow(particle, random);
    }

    @Override public void affectEntity(Entity entity, Level level) {
        primary.get().affectEntity(entity, level);
    }
}
