package expedition.refinery;

import java.util.List;
import java.util.Optional;

import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.material.Fluid;
import net.neoforged.neoforge.fluids.FluidStack;
import net.ty.createcraftedbeginning.api.gas.GasRegistries;

/** Material mappings at the refinery's existing fluid-backed inlets. */
public final class RefineryGasInputs {
    private static final TagKey<Fluid> STEAM = TagKey.create(Registries.FLUID, ResourceLocation.parse("c:steam"));
    private static final List<Input> INPUTS = List.of(
        new Input("createcraftedbeginning:steam", "mekanism:steam"),
        new Input("cmi:acetylene", "cmi:acetylene"),
        new Input("cmi:light_olefin", "cmi:light_olefin"),
        new Input("expedition:ethene", "mekanism:ethene")
    );

    public record Input(ResourceLocation gas, ResourceLocation fluid) {
        Input(String gas, String fluid) {
            this(ResourceLocation.parse(gas), ResourceLocation.parse(fluid));
        }

        public boolean matches(FluidStack stack) {
            return !stack.isEmpty() && (BuiltInRegistries.FLUID.getKey(stack.getFluid()).equals(fluid)
                || (gas.getNamespace().equals("createcraftedbeginning") && stack.is(STEAM)));
        }

        FluidStack stack(int amount) {
            return new FluidStack(BuiltInRegistries.FLUID.get(fluid), amount);
        }

        boolean registered() {
            return BuiltInRegistries.FLUID.containsKey(fluid) && GasRegistries.GAS_REGISTRY.containsKey(gas);
        }
    }

    private RefineryGasInputs() {}

    static Optional<Input> byGas(ResourceLocation gas) {
        return INPUTS.stream().filter(input -> input.gas().equals(gas) && input.registered()).findFirst();
    }

    public static Optional<Input> byFluid(FluidStack stack) {
        return INPUTS.stream().filter(input -> input.registered() && input.matches(stack)).findFirst();
    }
}
