package expedition.liquefied;

import net.minecraft.core.registries.Registries;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.FlowingFluid;

public final class PipedLiquids {
    private static final TagKey<Fluid> FLUIDS = TagKey.create(
        Registries.FLUID, ResourceLocation.fromNamespaceAndPath("expedition", "piped_liquefied_gases")
    );

    private PipedLiquids() {}

    public static boolean contains(Fluid fluid) {
        Fluid source = fluid instanceof FlowingFluid flowing ? flowing.getSource() : fluid;
        return BuiltInRegistries.FLUID.wrapAsHolder(source).is(FLUIDS);
    }
}
