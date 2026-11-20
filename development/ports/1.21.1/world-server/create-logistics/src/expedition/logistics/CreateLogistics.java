package expedition.logistics;

import com.simibubi.create.api.registry.CreateRegistries;
import com.simibubi.create.content.kinetics.mechanicalArm.ArmInteractionPoint;
import com.simibubi.create.content.kinetics.mechanicalArm.ArmInteractionPointType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.phys.Vec3;
import net.neoforged.bus.api.IEventBus;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.registries.RegisterEvent;
import vectorwing.farmersdelight.common.block.BasketBlock;

@Mod("expedition_create_logistics")
public final class CreateLogistics {
    public CreateLogistics(IEventBus bus) {
        bus.addListener(this::registerBasket);
        NeoForge.EVENT_BUS.addListener(LegacyLogisticsRepair::register);
    }

    private void registerBasket(RegisterEvent event) {
        // Retain the identifier stored by Central Kitchen in existing mechanical arms.
        event.register(CreateRegistries.ARM_INTERACTION_POINT_TYPE,
            ResourceLocation.fromNamespaceAndPath("create_central_kitchen", "basket"), BasketType::new);
    }

    private static final class BasketType extends ArmInteractionPointType {
        @Override
        public boolean canCreatePoint(Level level, BlockPos pos, BlockState state) {
            return state.getBlock() instanceof BasketBlock;
        }

        @Override
        public ArmInteractionPoint createPoint(Level level, BlockPos pos, BlockState state) {
            return new ArmInteractionPoint(this, level, pos, state) {
                @Override
                protected Vec3 getInteractionPositionVector() {
                    return Vec3.atCenterOf(pos);
                }

                @Override
                protected Direction getInteractionDirection() {
                    return Direction.UP;
                }
            };
        }
    }
}
