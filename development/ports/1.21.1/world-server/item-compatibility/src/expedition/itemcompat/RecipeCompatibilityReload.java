package expedition.itemcompat;

import java.util.Optional;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeInput;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;

public interface RecipeCompatibilityReload {
    void expedition$applyCompatibleItems();

    <I extends RecipeInput, T extends Recipe<I>> Optional<RecipeHolder<T>> expedition$preferOriginal(
        RecipeType<T> type, I input, Level level, Optional<RecipeHolder<T>> result);
}
