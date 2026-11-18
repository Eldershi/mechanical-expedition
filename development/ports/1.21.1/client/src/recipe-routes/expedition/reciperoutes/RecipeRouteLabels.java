package expedition.reciperoutes;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.datafixers.util.Either;
import java.io.IOException;
import java.nio.file.Files;
import java.util.HashSet;
import java.util.Set;
import mezz.jei.api.gui.IRecipeLayoutDrawable;
import mezz.jei.api.recipe.RecipeIngredientRole;
import mezz.jei.gui.recipes.RecipesGui;
import net.minecraft.ChatFormatting;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.fml.loading.FMLPaths;
import net.neoforged.neoforge.client.event.RenderTooltipEvent;
import net.neoforged.neoforge.common.NeoForge;
import org.slf4j.LoggerFactory;

@Mod(value = "expedition_recipe_route_labels", dist = Dist.CLIENT)
public final class RecipeRouteLabels {
    private static final Component ORIGINAL = Component.translatable("expedition.recipe_route.original")
        .withStyle(ChatFormatting.GRAY);
    private static final Component MODIFIED = Component.translatable("expedition.recipe_route.modified")
        .withStyle(ChatFormatting.GOLD);
    private final Routes overrides = Routes.read();

    public RecipeRouteLabels() {
        NeoForge.EVENT_BUS.addListener(this::addOutputLabel);
    }

    private void addOutputLabel(RenderTooltipEvent.GatherComponents event) {
        var client = Minecraft.getInstance();
        if (!(client.screen instanceof RecipesGui screen)) return;
        var window = client.getWindow();
        double x = client.mouseHandler.xpos() * window.getGuiScaledWidth() / window.getScreenWidth();
        double y = client.mouseHandler.ypos() * window.getGuiScaledHeight() / window.getScreenHeight();
        var hovered = screen.getRecipeLayoutUnderMouse(x, y);
        if (hovered.isEmpty()) return;
        var layout = hovered.get().getRecipeLayout();
        var output = layout.getRecipeSlotUnderMouse(x, y);
        if (output.isEmpty() || output.get().getRole() != RecipeIngredientRole.OUTPUT) return;
        if (!event.getItemStack().isEmpty()
                && output.get().getDisplayedItemStack().filter(stack -> net.minecraft.world.item.ItemStack
                    .isSameItemSameComponents(stack, event.getItemStack())).isEmpty()) return;
        var id = recipeId(layout);
        var label = id == null ? null : label(id);
        if (label != null && event.getTooltipElements().stream().noneMatch(element ->
                element.left().filter(label::equals).isPresent())) {
            event.getTooltipElements().add(Either.left(label));
        }
    }

    private static <R> ResourceLocation recipeId(IRecipeLayoutDrawable<R> layout) {
        return layout.getRecipeCategory().getRegistryName(layout.getRecipe());
    }

    private Component label(ResourceLocation id) {
        if (overrides.original().contains(id)) return ORIGINAL;
        if (overrides.modified().contains(id)) return MODIFIED;
        var path = id.getPath();
        if (id.getNamespace().equals("expedition")) {
            if (path.startsWith("selected_native/") || path.startsWith("pre_steam/") || path.equals("mixing/brass_ingot")) {
                return ORIGINAL;
            }
            if (path.startsWith("factory/") || path.startsWith("industry/") || path.startsWith("upstream_compat/")) {
                return MODIFIED;
            }
        }
        return id.getNamespace().equals("kubejs") || path.startsWith("kjs/") ? MODIFIED : null;
    }

    private record Routes(Set<ResourceLocation> original, Set<ResourceLocation> modified) {
        static Routes read() {
            var path = FMLPaths.GAMEDIR.get().resolve("kubejs/config/expedition-recipe-labels.json");
            if (Files.isRegularFile(path)) {
                try (var reader = Files.newBufferedReader(path)) {
                    var config = JsonParser.parseReader(reader).getAsJsonObject();
                    return new Routes(ids(config, "original"), ids(config, "modified"));
                } catch (IOException | RuntimeException error) {
                    LoggerFactory.getLogger(RecipeRouteLabels.class).warn("Could not load custom recipe route labels", error);
                }
            }
            return new Routes(Set.of(), Set.of());
        }

        private static Set<ResourceLocation> ids(JsonObject config, String key) {
            var values = config.get(key);
            if (values == null) return Set.of();
            Set<ResourceLocation> ids = new HashSet<>();
            for (JsonElement value : values.getAsJsonArray()) {
                ids.add(ResourceLocation.parse(value.getAsString()));
            }
            return Set.copyOf(ids);
        }
    }
}
