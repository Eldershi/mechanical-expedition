package expedition.performance.client;

import java.util.Map;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Read the existing ID index; neither cache nor change vanilla recipes. */
@Mixin(value = RecipeManager.class, remap = false)
public interface RecipeManagerAccess {
    @Accessor(value = "f_199900_", remap = false)
    Map<ResourceLocation, Recipe<?>> expedition$recipesById();
}
