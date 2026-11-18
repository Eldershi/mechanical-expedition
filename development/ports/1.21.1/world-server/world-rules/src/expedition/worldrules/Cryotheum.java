package expedition.worldrules;

import java.util.EnumSet;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceKey;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.damagesource.DamageType;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.level.BlockEvent;
import net.neoforged.neoforge.event.tick.EntityTickEvent;

final class Cryotheum {
    private static final ResourceLocation SOLUTION = ResourceLocation.parse("neoecoae:cryotheum_solution");
    private static final ResourceLocation GLACIOUS = ResourceLocation.parse("cmi:glacious_cryotheum");
    private static final ResourceKey<DamageType> CRYO_FUEL =
        ResourceKey.create(Registries.DAMAGE_TYPE, ResourceLocation.parse("ad_astra:cryo_fuel"));
    private static final Vec3 SLOWDOWN = new Vec3(0.9, 1.5, 0.9);
    private static final EnumSet<Direction> WATER_NEIGHBORS = EnumSet.complementOf(EnumSet.of(Direction.DOWN));

    private Cryotheum() {}

    static void register() {
        NeoForge.EVENT_BUS.addListener(Cryotheum::entityInFluid);
        NeoForge.EVENT_BUS.addListener(Cryotheum::checkFluidSpread);
    }

    private static void entityInFluid(EntityTickEvent.Post event) {
        if (!(event.getEntity() instanceof LivingEntity entity) || !entity.isAlive()) {
            return;
        }
        var level = entity.level();
        var position = entity.blockPosition();
        var state = level.getBlockState(position);
        if (state.getFluidState().isEmpty()) {
            return;
        }
        var id = BuiltInRegistries.BLOCK.getKey(state.getBlock());
        if (!SOLUTION.equals(id) && !GLACIOUS.equals(id)) {
            return;
        }
        entity.makeStuckInBlock(state, SLOWDOWN);
        entity.setIsInPowderSnow(true);
        entity.setTicksFrozen(Math.min(entity.getTicksRequiredToFreeze(), entity.getTicksFrozen() + 5));
        if (level.isClientSide) {
            var random = level.random;
            if ((entity.xOld != entity.getX() || entity.zOld != entity.getZ()) && random.nextBoolean()) {
                level.addParticle(ParticleTypes.SNOWFLAKE, entity.getX(), position.getY() + 1, entity.getZ(),
                    (random.nextDouble() - 0.5) / 6, 0.05, (random.nextDouble() - 0.5) / 6);
            }
        } else {
            entity.setSharedFlagOnFire(false);
            entity.setRemainingFireTicks(0);
            level.registryAccess().registryOrThrow(Registries.DAMAGE_TYPE).getHolder(CRYO_FUEL).ifPresent(type ->
                entity.hurt(new DamageSource(type), entity.fireImmune() ? 8 : 4));
        }
    }

    private static void checkFluidSpread(BlockEvent.NeighborNotifyEvent event) {
        if (!(event.getLevel() instanceof Level level) || level.isClientSide) {
            return;
        }
        var position = event.getPos();
        checkSolution(level, position);
        for (Direction direction : event.getNotifiedSides()) {
            checkSolution(level, position.relative(direction));
        }
    }

    private static void checkSolution(Level level, BlockPos position) {
        if (!level.isLoaded(position)) {
            return;
        }
        BlockState state = level.getBlockState(position);
        if (state.getFluidState().isEmpty() || !SOLUTION.equals(BuiltInRegistries.BLOCK.getKey(state.getBlock()))) {
            return;
        }
        for (Direction direction : WATER_NEIGHBORS) {
            var neighbor = position.relative(direction);
            if (level.isLoaded(neighbor) && level.getBlockState(neighbor).is(Blocks.WATER)) {
                level.setBlockAndUpdate(neighbor, Blocks.ICE.defaultBlockState());
                level.levelEvent(1501, position, 0);
                return;
            }
        }
        var fluid = state.getFluidState().getType();
        level.scheduleTick(position, fluid, fluid.getTickDelay(level));
    }
}
