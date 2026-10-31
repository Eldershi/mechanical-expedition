package expedition.performance.client;

import expedition.performance.policy.RecipeCountPolicy;

import java.util.Collection;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Pseudo;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** JECT 2.4.0-alpha.6 only uses this collection to read its size. */
@Pseudo
@Mixin(targets = "com.qwenteenn.just_enough_crafting_tree.recipe.RecipeSources", remap = false)
public abstract class JectRecipeCount {
    @Redirect(method = "fromClient", at = @At(value = "INVOKE",
        target = "Lnet/minecraft/world/item/crafting/RecipeManager;m_44051_()Ljava/util/Collection;",
        remap = false), remap = false, require = 1)
    private static Collection<Recipe<?>> expedition$readExistingRecipeIndex(RecipeManager manager) {
        if (!RecipeCountPolicy.enabled) return manager.m_44051_();
        return ((RecipeManagerAccess) manager).expedition$recipesById().values();
    }
}
