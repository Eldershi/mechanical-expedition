package expedition.space.mixin;

import com.simibubi.create.AllRecipeTypes;
import com.simibubi.create.content.processing.recipe.ProcessingInventory;
import com.simibubi.create.content.processing.recipe.StandardProcessingRecipe;
import com.simibubi.create.foundation.item.ItemHelper;
import java.util.ArrayList;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.entity.BlockEntityType;
import net.minecraft.world.level.block.state.BlockState;
import net.neoforged.neoforge.items.wrapper.RecipeWrapper;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets = "com.simibubi.create.content.kinetics.crusher.CrushingWheelControllerBlockEntity", remap = false)
abstract class EndStoneCrushingMixin extends BlockEntity {
    @Unique
    private static final ResourceLocation EXPEDITION_END_STONE =
        ResourceLocation.parse("expedition:factory/mineral_chemistry/end_stone_dust_manual_only");
    @Shadow public ProcessingInventory inventory;
    @Shadow private RecipeWrapper wrapper;
    @Shadow public abstract Optional<RecipeHolder<StandardProcessingRecipe<RecipeWrapper>>> findRecipe();

    private EndStoneCrushingMixin(BlockEntityType<?> type, BlockPos pos, BlockState state) {
        super(type, pos, state);
    }

    @Inject(method = "findRecipe", at = @At("RETURN"), cancellable = true)
    private void expedition$chooseEndStoneBatch(
        CallbackInfoReturnable<Optional<RecipeHolder<StandardProcessingRecipe<RecipeWrapper>>>> cir
    ) {
        var stack = inventory.getStackInSlot(0);
        if (level == null || !stack.is(Items.END_STONE)) return;
        var manager = level.getRecipeManager();
        var type = AllRecipeTypes.CRUSHING.<RecipeWrapper, StandardProcessingRecipe<RecipeWrapper>>getType();
        var recipes = manager.getAllRecipesFor(type);
        if (stack.getCount() >= 2) {
            recipes.stream().filter(holder -> holder.id().equals(EXPEDITION_END_STONE))
                .findFirst().ifPresent(holder -> cir.setReturnValue(Optional.of(holder)));
        } else if (cir.getReturnValue().filter(holder -> holder.id().equals(EXPEDITION_END_STONE)).isPresent()) {
            var nativeRecipe = recipes.stream().filter(holder -> !holder.id().equals(EXPEDITION_END_STONE))
                .filter(holder -> holder.value().matches(wrapper, level)).findFirst();
            cir.setReturnValue(nativeRecipe.or(() -> AllRecipeTypes.MILLING.find(wrapper, level)));
        }
    }

    @Inject(method = "applyRecipe", at = @At("HEAD"), cancellable = true)
    private void expedition$applyEndStoneBatch(CallbackInfo ci) {
        if (level == null) return;
        var stack = inventory.getStackInSlot(0);
        if (!stack.is(Items.END_STONE) || stack.getCount() < 2) return;
        var match = findRecipe().filter(holder -> holder.id().equals(EXPEDITION_END_STONE));
        if (match.isEmpty()) return;

        var recipe = match.orElseThrow().value();
        var outputs = new ArrayList<ItemStack>();
        for (int i = 0; i < stack.getCount() / 2; i++) {
            for (var output : recipe.rollResults(level.random)) ItemHelper.addToList(output, outputs);
        }
        if ((stack.getCount() & 1) != 0) outputs.add(stack.copyWithCount(1));

        inventory.clear();
        for (int i = 0; i < outputs.size(); i++) inventory.setStackInSlot(i + 1, outputs.get(i));
        ci.cancel();
    }
}
