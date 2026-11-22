package expedition.alloyfurnace;

import com.lowdragmc.mbd2.common.machine.MBDMachine;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.fml.common.Mod;

@Mod("expedition_alloy_furnace")
public final class AlloyFurnace {
    private static final ResourceLocation CONTROLLER = ResourceLocation.parse("expedition_industry:alloy_furnace");

    public static boolean isController(MBDMachine machine) {
        return CONTROLLER.equals(machine.getDefinition().id());
    }
}
