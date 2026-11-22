package expedition.alloyfurnace;

import com.lowdragmc.mbd2.common.machine.MBDMachine;
import java.util.Set;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.fml.common.Mod;

@Mod("expedition_alloy_furnace")
public final class AlloyFurnace {
    private static final ResourceLocation CONTROLLER = ResourceLocation.parse("expedition_industry:alloy_furnace");

    private static final ResourceLocation HYDRAULIC_PRESS = ResourceLocation.parse("expedition_industry:hydropress");

    private static final Set<ResourceLocation> PHYSICAL_PORTS = Set.of(CONTROLLER, HYDRAULIC_PRESS,
        ResourceLocation.parse("expedition_industry:shaft_furnace"),
        ResourceLocation.parse("expedition_industry:electrolytic_cell"),
        ResourceLocation.parse("expedition_industry:trading_station"));

    public static boolean usesPhysicalPorts(MBDMachine machine) {
        return PHYSICAL_PORTS.contains(machine.getDefinition().id());
    }

    public static boolean isHydraulicPress(MBDMachine machine) {
        return HYDRAULIC_PRESS.equals(machine.getDefinition().id());
    }
}
