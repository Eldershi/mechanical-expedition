package expedition.alloyfurnace;

import com.lowdragmc.mbd2.common.machine.MBDMachine;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.fml.common.Mod;

@Mod("expedition_alloy_furnace")
public final class AlloyFurnace {
    private static final ResourceLocation CONTROLLER = ResourceLocation.parse("expedition_industry:alloy_furnace");

    private static final ResourceLocation HYDRAULIC_PRESS = ResourceLocation.parse("expedition_industry:hydropress");

    public static boolean usesPhysicalPorts(MBDMachine machine) {
        var id = machine.getDefinition().id();
        return CONTROLLER.equals(id) || isHydraulicPress(machine);
    }

    public static boolean isHydraulicPress(MBDMachine machine) {
        return HYDRAULIC_PRESS.equals(machine.getDefinition().id());
    }
}
