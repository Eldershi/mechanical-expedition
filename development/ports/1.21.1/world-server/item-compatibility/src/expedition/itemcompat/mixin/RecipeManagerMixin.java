package expedition.itemcompat.mixin;

import com.google.gson.JsonElement;
import com.google.common.collect.ImmutableMap;
import com.google.common.collect.ImmutableMultimap;
import com.google.common.collect.Multimap;
import expedition.itemcompat.RecipeCompatibilityReload;
import expedition.itemcompat.RecipeItemCompatibility;
import java.util.Collection;
import java.util.HashSet;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.util.profiling.ProfilerFiller;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import net.minecraft.world.item.crafting.RecipeInput;
import net.minecraft.world.item.crafting.RecipeManager;
import net.minecraft.world.item.crafting.RecipeType;
import net.minecraft.world.level.Level;
import org.spongepowered.asm.mixin.Final;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = RecipeManager.class, priority = 500)
abstract class RecipeManagerMixin implements RecipeCompatibilityReload {
    @Shadow @Final private HolderLookup.Provider registries;
    @Shadow private Map<ResourceLocation, RecipeHolder<?>> byName;
    @Shadow private Multimap<RecipeType<?>, RecipeHolder<?>> byType;
    @Shadow private <I extends RecipeInput, T extends Recipe<I>> Collection<RecipeHolder<T>> byType(RecipeType<T> type) {
        throw new AssertionError();
    }

    @Unique private Map<ResourceLocation, RecipeItemCompatibility.Original> expedition$originalRecipes = Map.of();
    @Unique private ResourceManager expedition$recipeResources;

    @Inject(method = "apply(Ljava/util/Map;Lnet/minecraft/server/packs/resources/ResourceManager;"
        + "Lnet/minecraft/util/profiling/ProfilerFiller;)V", at = @At("TAIL"))
    private void expedition$rememberRecipeResources(Map<ResourceLocation, JsonElement> data,
            ResourceManager resources, ProfilerFiller profiler, CallbackInfo callback) {
        expedition$recipeResources = resources;
    }

    @Override
    public void expedition$applyCompatibleItems() {
        if (expedition$recipeResources == null) {
            return;
        }
        var resources = expedition$recipeResources;
        expedition$recipeResources = null;
        var updated = RecipeItemCompatibility.apply(resources, registries, byName.values());
        expedition$originalRecipes = updated == null ? Map.of() : updated.originals();
        if (updated != null) {
            var byId = ImmutableMap.<ResourceLocation, RecipeHolder<?>>builder();
            for (var holder : updated.recipes()) {
                byId.put(holder.id(), holder);
            }
            var replacements = byId.buildOrThrow();
            var ordered = ImmutableMultimap.<RecipeType<?>, RecipeHolder<?>>builder();
            for (var entry : byType.entries()) {
                var holder = replacements.getOrDefault(entry.getValue().id(), entry.getValue());
                ordered.put(entry.getKey(), holder);
            }
            byName = replacements;
            byType = ordered.build();
        }
    }

    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
        + "Lnet/minecraft/world/item/crafting/RecipeInput;Lnet/minecraft/world/level/Level;"
        + "Lnet/minecraft/world/item/crafting/RecipeHolder;)Ljava/util/Optional;", at = @At("RETURN"),
        cancellable = true)
    private <I extends RecipeInput, T extends Recipe<I>> void expedition$preferOriginalMatch(
            RecipeType<T> type, I input, Level level, RecipeHolder<T> cached,
            CallbackInfoReturnable<Optional<RecipeHolder<T>>> callback) {
        var current = callback.getReturnValue();
        var preferred = expedition$preferOriginal(type, input, level, current);
        if (preferred != current) {
            callback.setReturnValue(preferred);
        }
    }

    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
        + "Lnet/minecraft/world/item/crafting/RecipeInput;Lnet/minecraft/world/level/Level;)"
        + "Ljava/util/Optional;", at = @At("HEAD"), order = 100, cancellable = true)
    private <I extends RecipeInput, T extends Recipe<I>> void expedition$preferOriginalUncached(
            RecipeType<T> type, I input, Level level, CallbackInfoReturnable<Optional<RecipeHolder<T>>> callback) {
        if (!expedition$originalRecipes.isEmpty()) {
            callback.setReturnValue(((RecipeManager) (Object) this)
                .getRecipeFor(type, input, level, (ResourceLocation) null));
        }
    }

    @Inject(method = "getRecipeFor(Lnet/minecraft/world/item/crafting/RecipeType;"
        + "Lnet/minecraft/world/item/crafting/RecipeInput;Lnet/minecraft/world/level/Level;"
        + "Lnet/minecraft/resources/ResourceLocation;)Ljava/util/Optional;", at = @At("RETURN"),
        cancellable = true)
    private <I extends RecipeInput, T extends Recipe<I>> void expedition$preferOriginalById(
            RecipeType<T> type, I input, Level level, ResourceLocation cached,
            CallbackInfoReturnable<Optional<RecipeHolder<T>>> callback) {
        var current = callback.getReturnValue();
        var preferred = expedition$preferOriginal(type, input, level, current);
        if (preferred != current) {
            callback.setReturnValue(preferred);
        }
    }

    @Override
    public <I extends RecipeInput, T extends Recipe<I>> Optional<RecipeHolder<T>> expedition$preferOriginal(
            RecipeType<T> type, I input, Level level, Optional<RecipeHolder<T>> result) {
        var match = result.orElse(null);
        if (match == null) {
            return result;
        }
        var selected = expedition$originalRecipes.get(match.id());
        if (selected == null) {
            return result;
        }
        Set<String> used = new HashSet<>();
        for (int slot = 0; slot < input.size(); slot++) {
            var stack = input.getItem(slot);
            if (!stack.isEmpty()) {
                used.add(BuiltInRegistries.ITEM.getKey(stack.getItem()).toString());
            }
        }
        if (selected.items().containsAll(used) && expedition$matchesOriginal(selected.recipe(), input, level)) {
            return result;
        }
        for (var candidate : byType(type)) {
            var original = expedition$originalRecipes.get(candidate.id());
            if (original == null ? candidate.value().matches(input, level)
                    : original.items().containsAll(used) && expedition$matchesOriginal(original.recipe(), input, level)) {
                return Optional.of(candidate);
            }
        }
        return result;
    }

    @Unique
    @SuppressWarnings("unchecked")
    private <I extends RecipeInput> boolean expedition$matchesOriginal(Recipe<?> recipe, I input, Level level) {
        return ((Recipe<I>) recipe).matches(input, level);
    }
}
