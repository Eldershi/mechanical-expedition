package expedition.refinery.mixin;

import java.util.Arrays;
import java.util.List;

import blusunrize.immersiveengineering.api.crafting.RefineryRecipe;
import blusunrize.immersiveengineering.common.util.compat.jei.refinery.RefineryRecipeCategory;
import expedition.refinery.RefineryGasInputs;
import mezz.jei.api.gui.builder.IRecipeLayoutBuilder;
import mezz.jei.api.gui.drawable.IDrawableStatic;
import mezz.jei.api.neoforge.NeoForgeTypes;
import mezz.jei.api.recipe.IFocusGroup;
import mezz.jei.api.recipe.RecipeIngredientRole;
import net.neoforged.neoforge.fluids.FluidStack;
import net.neoforged.neoforge.fluids.crafting.SizedFluidIngredient;
import net.ty.createcraftedbeginning.api.gas.GasRegistries;
import net.ty.createcraftedbeginning.api.gas.GasStack;
import net.ty.createcraftedbeginning.compat.jei.CCBJEIPlugin;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = RefineryRecipeCategory.class, remap = false)
public abstract class RefineryJeiMixin {
    @Shadow @Final private IDrawableStatic tankOverlay;

    @Inject(method = "setRecipe(Lmezz/jei/api/gui/builder/IRecipeLayoutBuilder;Lblusunrize/immersiveengineering/api/crafting/RefineryRecipe;Lmezz/jei/api/recipe/IFocusGroup;)V",
            at = @At("HEAD"), cancellable = true)
    private void expedition$showGasInputs(IRecipeLayoutBuilder builder, RefineryRecipe recipe, IFocusGroup focus,
                                          CallbackInfo callback) {
        List<GasStack> first = expedition$gases(recipe.input0);
        List<GasStack> second = expedition$gases(recipe.input1);
        if (first.isEmpty() && second.isEmpty()) return;

        expedition$input(builder, recipe.input0, first, 7);
        expedition$input(builder, recipe.input1, second, 34);
        if (!recipe.catalyst.isEmpty()) {
            builder.addSlot(RecipeIngredientRole.CATALYST, 67, 16).addItemStacks(Arrays.asList(recipe.catalyst.getItems()));
        }
        builder.addSlot(RecipeIngredientRole.OUTPUT, 103, 10).setFluidRenderer(50, false, 16, 47)
            .setOverlay(tankOverlay, 0, 0).addIngredient(NeoForgeTypes.FLUID_STACK, recipe.output);
        callback.cancel();
    }

    @Unique
    private static List<GasStack> expedition$gases(SizedFluidIngredient ingredient) {
        if (ingredient == null) return List.of();
        return Arrays.stream(ingredient.getFluids()).flatMap(fluid -> RefineryGasInputs.byFluid(fluid).stream()
            .map(input -> new GasStack(GasRegistries.GAS_REGISTRY.get(input.gas()), fluid.getAmount())))
            .distinct().toList();
    }

    @Unique
    private void expedition$input(IRecipeLayoutBuilder builder, SizedFluidIngredient ingredient, List<GasStack> gases,
                                  int x) {
        if (ingredient == null) return;
        List<FluidStack> fluids = Arrays.asList(ingredient.getFluids());
        if (gases.isEmpty()) {
            builder.addSlot(RecipeIngredientRole.INPUT, x, 10).setFluidRenderer(50, false, 16, 47)
                .setOverlay(tankOverlay, 0, 0).addIngredients(NeoForgeTypes.FLUID_STACK, fluids);
        } else {
            builder.addSlot(RecipeIngredientRole.INPUT, x, 24).addIngredients(CCBJEIPlugin.GAS_STACK, gases);
            builder.addInvisibleIngredients(RecipeIngredientRole.INPUT).addIngredients(NeoForgeTypes.FLUID_STACK, fluids);
        }
    }
}
