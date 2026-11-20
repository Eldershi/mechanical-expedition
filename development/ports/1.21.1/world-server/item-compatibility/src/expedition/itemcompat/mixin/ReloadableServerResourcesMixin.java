package expedition.itemcompat.mixin;

import expedition.itemcompat.RecipeCompatibilityReload;
import net.minecraft.server.ReloadableServerResources;
import net.minecraft.world.item.crafting.RecipeManager;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = ReloadableServerResources.class, priority = 500)
abstract class ReloadableServerResourcesMixin {
    @Shadow public abstract RecipeManager getRecipeManager();

    @Inject(method = "updateRegistryTags()V", at = @At("TAIL"), order = 1100)
    private void expedition$applyAfterRecipeGeneration(CallbackInfo callback) {
        ((RecipeCompatibilityReload) getRecipeManager()).expedition$applyCompatibleItems();
    }
}
