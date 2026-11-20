package expedition.itemcompat.mixin;

import expedition.itemcompat.RecipeCompatibilityReload;
import java.util.Optional;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeInput;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets = "dev.shadowsoffire.fastsuite.AuxRecipeManager", remap = false)
abstract class FastSuiteRecipeManagerMixin {
    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
        + "Lnet/minecraft/world/item/crafting/RecipeInput;Lnet/minecraft/world/level/Level;"
        + "Lnet/minecraft/world/item/crafting/RecipeHolder;)Ljava/util/Optional;", at = @At("RETURN"),
        cancellable = true)
    private <I extends RecipeInput, T extends Recipe<I>> void expedition$preferOriginalMatch(
            RecipeType<T> type, I input, Level level, RecipeHolder<T> cached,
            CallbackInfoReturnable<Optional<RecipeHolder<T>>> callback) {
        var current = callback.getReturnValue();
        var preferred = ((RecipeCompatibilityReload) this).expedition$preferOriginal(type, input, level, current);
        if (preferred != current) {
            callback.setReturnValue(preferred);
        }
    }
}
