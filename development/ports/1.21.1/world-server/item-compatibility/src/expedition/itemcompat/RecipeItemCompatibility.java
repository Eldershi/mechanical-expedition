package expedition.itemcompat;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.lowdragmc.mbd2.api.recipe.MBDRecipe;
import com.mojang.logging.LogUtils;
import com.mojang.serialization.DynamicOps;
import com.mojang.serialization.JsonOps;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import net.minecraft.core.HolderLookup;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.packs.resources.ResourceManager;
import net.minecraft.tags.TagKey;
import net.minecraft.world.item.crafting.Recipe;
import net.minecraft.world.item.crafting.RecipeHolder;
import org.slf4j.Logger;

public final class RecipeItemCompatibility {
    public record Original(Recipe<?> recipe, Set<String> items) {}

    public record Result(List<RecipeHolder<?>> recipes, Map<ResourceLocation, Original> originals) {}

    private static final Logger LOGGER = LogUtils.getLogger();
    private static final ResourceLocation RULES = ResourceLocation.parse("expedition:item_compatibility.json");
    private static final Set<String> OUTPUTS = Set.of("result", "results", "output", "outputs", "itemOutput",
        "resultItem", "item_output", "item_results", "fluid_output", "chemical_output", "byproducts", "slag",
        "secondaryOutputs", "processing_results", "outputItems", "outputItem", "main_output", "secondary_output");
    private static final Set<String> METADATA = Set.of("components", "nbt", "neoforge:conditions", "conditions",
        "icon", "display", "using", "template", "transitionalItem", "transitional_item", "transitional",
        "fluid", "fluids", "fluid_input", "fluid_inputs", "chemical_input", "gas_ingredients", "data");
    private static final Set<String> INGREDIENT_KEYS = Set.of("item", "tag", "count");

    private final Map<String, Set<String>> alternatives;
    private final Map<String, Set<String>> tagItems = new HashMap<>();

    private RecipeItemCompatibility(Map<String, Set<String>> alternatives) {
        this.alternatives = alternatives;
    }

    public static Result apply(ResourceManager resources, HolderLookup.Provider registries,
                               Collection<RecipeHolder<?>> recipes) {
        var resource = resources.getResource(RULES);
        if (resource.isEmpty()) {
            return null;
        }
        Map<String, Set<String>> equivalents = new HashMap<>();
        try (var reader = resource.get().openAsReader()) {
            for (var entry : JsonParser.parseReader(reader).getAsJsonObject().getAsJsonArray("groups")) {
                Set<String> group = new LinkedHashSet<>();
                for (var member : entry.getAsJsonArray()) {
                    String id = member.getAsString();
                    if (!id.equals("minecraft:air") && BuiltInRegistries.ITEM.containsKey(ResourceLocation.parse(id))) {
                        group.add(id);
                    }
                }
                if (group.size() > 1) {
                    for (var item : group) {
                        equivalents.computeIfAbsent(item, key -> new LinkedHashSet<>()).addAll(group);
                    }
                }
            }
        } catch (IOException | RuntimeException error) {
            LOGGER.error("Could not load Expedition recipe item compatibility", error);
            return null;
        }
        return new RecipeItemCompatibility(equivalents)
            .apply(recipes, registries.createSerializationContext(JsonOps.INSTANCE));
    }

    private Result apply(Collection<RecipeHolder<?>> recipes, DynamicOps<JsonElement> ops) {
        List<RecipeHolder<?>> updated = new ArrayList<>(recipes.size());
        Map<ResourceLocation, Original> originals = new HashMap<>();
        Map<String, Integer> skipped = new TreeMap<>();
        for (var holder : recipes) {
            RecipeHolder<?> result = holder;
            try {
                result = rewrite(holder, ops, skipped, originals);
            } catch (RuntimeException error) {
                LOGGER.debug("Could not inspect recipe {}", holder.id(), error);
            }
            updated.add(result);
        }
        LOGGER.info("Expedition item compatibility extended {} recipes across {} item IDs",
            originals.size(), alternatives.size());
        if (!skipped.isEmpty()) {
            LOGGER.warn("Expedition retained recipe serializers which require a specific ingredient format: {}", skipped);
        }
        return originals.isEmpty() ? null : new Result(updated, Map.copyOf(originals));
    }

    private RecipeHolder<?> rewrite(RecipeHolder<?> holder, DynamicOps<JsonElement> ops,
                                     Map<String, Integer> skipped, Map<ResourceLocation, Original> originals) {
        var recipe = holder.value();
        var original = Recipe.CODEC.encodeStart(ops, recipe).result().orElse(null);
        if (original == null || !original.isJsonObject()) {
            return holder;
        }
        Set<String> outputs = new HashSet<>();
        collectOutputs(original, outputs);
        var candidate = expand(original, outputs);
        if (original.equals(candidate)) {
            return holder;
        }
        try {
            var replacement = Recipe.CODEC.parse(ops, candidate).result().orElse(null);
            if (recipe instanceof MBDRecipe originalMachine && replacement instanceof MBDRecipe machine) {
                machine.recipeType = originalMachine.recipeType;
            }
            if (replacement != null && replacement.getType() == recipe.getType()
                    && replacement.getSerializer() == recipe.getSerializer()
                    && Recipe.CODEC.encodeStart(ops, replacement).result()
                    .filter(candidate::equals).isPresent()) {
                Set<String> ingredients = new HashSet<>();
                collectInputs(original, ingredients);
                originals.put(holder.id(), new Original(recipe, Set.copyOf(ingredients)));
                return new RecipeHolder<>(holder.id(), replacement);
            }
        } catch (RuntimeException error) {
            LOGGER.debug("Recipe {} rejected compatible inputs", holder.id(), error);
        }
        skipped.merge(string(original.getAsJsonObject(), "type"), 1, Integer::sum);
        return holder;
    }

    private JsonElement expand(JsonElement node, Set<String> outputs) {
        if (node.isJsonArray()) {
            var expanded = new JsonArray();
            for (var entry : node.getAsJsonArray()) {
                expanded.add(expand(entry, outputs));
            }
            return expanded;
        }
        if (!node.isJsonObject()) {
            return node;
        }
        var fields = node.getAsJsonObject();
        if (fields.has("type") && !string(fields, "type").equals("neoforge:compound")) {
            // An ingredient that compares components or implements a custom predicate keeps its own matcher.
            if (!fields.has("ingredients") && !fields.has("inputs") && !fields.has("ingredient")
                    && !fields.has("input") && !fields.has("key") && !fields.has("sequence")
                    && !fields.has("item_input") && !fields.has("cast") && !fields.has("base")
                    && !fields.has("addition") && !fields.has("inputItems")) {
                return node;
            }
        }
        if (!fields.entrySet().isEmpty() && INGREDIENT_KEYS.containsAll(fields.keySet())) {
            var compatible = expandIngredient(fields, outputs);
            if (compatible != fields) {
                return compatible;
            }
        }
        var expanded = new JsonObject();
        for (var field : fields.entrySet()) {
            var name = field.getKey();
            var value = field.getValue();
            expanded.add(name, OUTPUTS.contains(name) || METADATA.contains(name) ? value : expand(value, outputs));
        }
        return expanded;
    }

    private JsonObject expandIngredient(JsonObject ingredient, Set<String> outputs) {
        var direct = string(ingredient, "item");
        var tag = string(ingredient, "tag");
        if (direct.isEmpty() && tag.isEmpty()) {
            return ingredient;
        }
        var accepted = direct.isEmpty() ? itemsInTag(tag) : Set.of(direct);
        Set<String> extra = new LinkedHashSet<>();
        for (var item : accepted) {
            extra.addAll(alternatives.getOrDefault(item, Set.of()));
        }
        extra.removeAll(accepted);
        if (extra.isEmpty() || extra.stream().anyMatch(outputs::contains)) {
            return ingredient;
        }
        var alias = "expedition:recipe_aliases/" + (direct.isEmpty() ? "tag/" + tag : "item/" + direct)
            .replace(':', '/');
        var registered = itemsInTag(alias);
        if (registered.isEmpty() || !registered.containsAll(accepted) || !registered.containsAll(extra)) {
            return ingredient;
        }
        var expanded = new JsonObject();
        expanded.addProperty("tag", alias);
        if (ingredient.has("count")) {
            expanded.add("count", ingredient.get("count"));
        }
        return expanded;
    }

    private Set<String> itemsInTag(String tag) {
        if (tag.isEmpty()) {
            return Set.of();
        }
        return tagItems.computeIfAbsent(tag, key -> {
            Set<String> items = new LinkedHashSet<>();
            var id = ResourceLocation.tryParse(key);
            if (id != null) {
                BuiltInRegistries.ITEM.getTagOrEmpty(TagKey.create(Registries.ITEM, id))
                    .forEach(holder -> items.add(BuiltInRegistries.ITEM.getKey(holder.value()).toString()));
            }
            return items;
        });
    }

    private void collectInputs(JsonElement node, Set<String> items) {
        if (node.isJsonArray()) {
            node.getAsJsonArray().forEach(entry -> collectInputs(entry, items));
        } else if (node.isJsonObject()) {
            var json = node.getAsJsonObject();
            if (INGREDIENT_KEYS.containsAll(json.keySet())) {
                var item = string(json, "item");
                var tag = string(json, "tag");
                if (!item.isEmpty()) {
                    items.add(item);
                } else if (!tag.isEmpty()) {
                    items.addAll(itemsInTag(tag));
                }
            } else {
                for (var field : json.entrySet()) {
                    if (!OUTPUTS.contains(field.getKey()) && !METADATA.contains(field.getKey())) {
                        collectInputs(field.getValue(), items);
                    }
                }
            }
        }
    }

    private static void collectOutputs(JsonElement node, Set<String> outputs) {
        if (node.isJsonArray()) {
            node.getAsJsonArray().forEach(entry -> collectOutputs(entry, outputs));
        } else if (node.isJsonObject()) {
            for (var field : node.getAsJsonObject().entrySet()) {
                if (OUTPUTS.contains(field.getKey())) {
                    collectItems(field.getValue(), outputs);
                } else if (!METADATA.contains(field.getKey())) {
                    collectOutputs(field.getValue(), outputs);
                }
            }
        }
    }

    private static void collectItems(JsonElement node, Set<String> outputs) {
        if (node.isJsonArray()) {
            node.getAsJsonArray().forEach(value -> collectItems(value, outputs));
        } else if (node.isJsonObject()) {
            node.getAsJsonObject().entrySet().forEach(field -> {
                if (!METADATA.contains(field.getKey())) {
                    collectItems(field.getValue(), outputs);
                }
            });
        } else if (node.isJsonPrimitive() && node.getAsJsonPrimitive().isString()) {
            var id = ResourceLocation.tryParse(node.getAsString());
            if (id != null && BuiltInRegistries.ITEM.containsKey(id)) {
                outputs.add(id.toString());
            }
        }
    }

    private static String string(JsonObject json, String key) {
        var value = json.get(key);
        return value != null && value.isJsonPrimitive() && value.getAsJsonPrimitive().isString()
            ? value.getAsString() : "";
    }
}
