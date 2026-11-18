package expedition.flight.mixin;

import java.util.List;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeInput;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

@Mixin(targets = "studio.fantasyit.maid_storage_manager.craft.generator.type.create.GeneratorCreate")
abstract class MaidCreateRecipesMixin {
    @Redirect(method = {"onCache", "addRecipeForPos"}, at = @At(value = "INVOKE",
        target = "Lnet/minecraft/world/item/crafting/RecipeManager;getAllRecipesFor(Lnet/minecraft/world/item/crafting/RecipeType;)Ljava/util/List;"),
        require = 2)
    private <I extends RecipeInput, T extends Recipe<I>> List<RecipeHolder<T>> expedition$normalBasinProcesses(
            RecipeManager manager, RecipeType<T> type) {
        return manager.getAllRecipesFor(type).stream()
            .filter(holder -> {
                ResourceLocation serializer = BuiltInRegistries.RECIPE_SERIALIZER.getKey(holder.value().getSerializer());
                return serializer == null || !serializer.getNamespace().equals("createcraftedbeginning")
                    || !(serializer.getPath().equals("chilled_compacting") || serializer.getPath().equals("chilled_mixing"));
            }).toList();
    }
}
