import dev.ftb.mods.ftblibrary.snbt.SNBT;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;

final class ConvertItemFilters {
    private static final String LEGACY = "itemfilters:";
    private static final String SMART_FILTER = "ftbfiltersystem:smart_filter";
    private static final String FILTER_COMPONENT = "ftbfiltersystem:filter";
    private static final Pattern RESOURCE_ID = Pattern.compile("[a-z0-9_.-]+:[a-z0-9_.\\-/]+");
    private static final Set<String> STACK_FIELDS = Set.of("item", "icon");
    private static final Set<String> OBJECT_FIELDS = Set.of(
            "title", "subtitle", "description", "icon", "item", "count",
            "dependencies", "advancement", "omit_tasks");

    private record ConvertedFile(Path relative, CompoundTag contents, int count) {}
    private record Mappings(CompoundTag items, CompoundTag tags, CompoundTag stacks, CompoundTag objects) {
        Mappings(CompoundTag source) {
            this(source.getCompound("items"), source.getCompound("tags"),
                    source.getCompound("component_stacks"), source.getCompound("objects"));
        }
    }

    public static void main(String[] args) throws IOException {
        if (args.length < 2 || args.length > 3) {
            throw new IllegalArgumentException(
                    "Usage: ConvertItemFilters <quest source> <new output directory> [item and tag mappings]");
        }
        Path source = Path.of(args[0]).toRealPath();
        Path output = Path.of(args[1]).toAbsolutePath().normalize();
        var mappingInput = args.length == 3 ? SNBT.read(Path.of(args[2])) : new CompoundTag();
        if (mappingInput == null) throw new IllegalArgumentException("Could not read quest mappings");
        var mappings = new Mappings(mappingInput);
        if (!Files.isDirectory(source) || Files.exists(output) || output.startsWith(source)) {
            throw new IllegalArgumentException("Use an existing source directory and a separate new output directory");
        }

        var converted = new ArrayList<ConvertedFile>();
        try (var files = Files.walk(source)) {
            for (Path file : files.filter(Files::isRegularFile).filter(path -> path.toString().endsWith(".snbt")).sorted().toList()) {
                if (args.length == 2 && !Files.readString(file).contains(LEGACY)) continue;
                try {
                    CompoundTag contents = SNBT.read(file);
                    if (contents == null) throw new IllegalArgumentException("Could not read SNBT");
                    int count = convert(contents, mappings, false);
                    if (args.length == 3 || count > 0) {
                        converted.add(new ConvertedFile(source.relativize(file), contents, count));
                    }
                } catch (IllegalArgumentException e) {
                    throw new IllegalArgumentException(file.getFileName() + ": " + e.getMessage(), e);
                }
            }
        }
        Files.createDirectories(output);
        for (ConvertedFile file : converted) {
            Path target = output.resolve(file.relative());
            Files.createDirectories(target.getParent());
            if (!SNBT.write(target, file.contents())) throw new IOException("Could not write " + target);
            System.out.printf("%s: %d%n", file.relative(), file.count());
        }
        System.out.printf("Converted %d legacy filter stacks across %d files%n",
                converted.stream().mapToInt(ConvertedFile::count).sum(),
                converted.stream().filter(file -> file.count() > 0).count());
    }

    private static int convert(Tag node, Mappings mappings, boolean itemTask) {
        int converted = 0;
        if (node instanceof CompoundTag tag) {
            if (tag.getString("id").startsWith(LEGACY)) {
                String expression = filter(tag, mappings);
                int count = tag.contains("Count", Tag.TAG_ANY_NUMERIC) ? tag.getInt("Count") : 1;
                if (count != 1) throw new IllegalArgumentException("Smart Filters require a stack count of one");
                tag.remove("Count");
                tag.remove("tag");
                tag.putString("id", SMART_FILTER);
                tag.putInt("count", count);
                var components = new CompoundTag();
                components.putString(FILTER_COMPONENT, expression);
                tag.put("components", components);
                return 1;
            }
            String id = tag.getString("id");
            if (mappings.objects().contains(id)) {
                var fields = mappings.objects().getCompound(id);
                requireKeys(fields, OBJECT_FIELDS);
                for (String key : fields.getAllKeys()) {
                    switch (key) {
                        case "omit_tasks" -> omitTasks(tag, fields.getList(key, Tag.TAG_STRING));
                        case "advancement" -> {
                            if (!itemTask || !tag.getString("type").equals("item")) {
                                throw new IllegalArgumentException("Expected item task " + id);
                            }
                            tag.remove("item");
                            tag.remove("count");
                            tag.remove("consume_items");
                            tag.remove("only_from_crafting");
                            tag.remove("match_components");
                            tag.putString("type", "advancement");
                            tag.putString("advancement", resource(fields.getString(key)));
                            tag.putString("criterion", "");
                        }
                        default -> tag.put(key, fields.get(key).copy());
                    }
                }
            }
            for (String key : List.copyOf(tag.getAllKeys())) {
                Tag child = tag.get(key);
                if (STACK_FIELDS.contains(key)) {
                    Tag replacement = mapStack(child, mappings);
                    if (replacement != child) tag.put(key, replacement);
                    if (itemTask && key.equals("item") && replacement instanceof CompoundTag newStack
                            && replacement != child && newStack.contains("components")) tag.putString("match_components", "strict");
                    child = replacement;
                }
                converted += convert(child, mappings, key.equals("tasks"));
            }
        } else if (node instanceof ListTag list) {
            for (Tag entry : list) converted += convert(entry, mappings, itemTask);
        }
        return converted;
    }

    private static void omitTasks(CompoundTag quest, ListTag omitted) {
        ListTag tasks = quest.getList("tasks", Tag.TAG_COMPOUND);
        if (omitted.isEmpty() || omitted.size() >= tasks.size()) {
            throw new IllegalArgumentException("Quest must keep at least one task: " + quest.getString("id"));
        }
        for (Tag item : omitted) {
            String id = item.getAsString();
            if (!tasks.removeIf(task -> ((CompoundTag) task).getString("id").equals(id))) {
                throw new IllegalArgumentException("Unknown task " + id + " in " + quest.getString("id"));
            }
        }
    }

    private static Tag mapStack(Tag node, Mappings mappings) {
        CompoundTag stack = node instanceof CompoundTag compound ? compound : null;
        String id;
        if (stack != null) id = stack.getString("id");
        else if (node instanceof StringTag string) id = string.getAsString();
        else return node;
        if (mappings.stacks().contains(id)) {
            var replacement = mappings.stacks().getCompound(id).copy();
            resource(replacement.getString("id"));
            if (stack != null) {
                requireKeys(stack, Set.of("id", "Count", "count"));
                if (stack.contains("Count")) replacement.putInt("count", stack.getInt("Count"));
                if (stack.contains("count")) replacement.putInt("count", stack.getInt("count"));
            }
            return replacement;
        }
        if (mappings.items().contains(id)) {
            String target = resource(mappings.items().getString(id));
            if (stack == null) return StringTag.valueOf(target);
            stack.putString("id", target);
        }
        return node;
    }

    private static String filter(CompoundTag stack, Mappings mappings) {
        String id = stack.getString("id");
        CompoundTag settings = stack.getCompound("tag");
        return switch (id) {
            case "itemfilters:tag" -> {
                requireKeys(stack, Set.of("id", "Count", "tag"));
                requireKeys(settings, Set.of("value"));
                String value = resource(settings.getString("value"));
                if (value.startsWith("forge:")) value = "c:" + value.substring("forge:".length());
                var tags = mappings.tags();
                String replacement = tags.contains(value) ? tags.getString(value) : "#" + value;
                yield replacement.startsWith("#")
                        ? "item_tag(" + resource(replacement.substring(1)) + ")"
                        : "item(" + resource(replacement) + ")";
            }
            case "itemfilters:or" -> {
                requireKeys(stack, Set.of("id", "Count", "tag"));
                requireKeys(settings, Set.of("items"));
                ListTag alternatives = settings.getList("items", Tag.TAG_COMPOUND);
                if (alternatives.isEmpty()) throw new IllegalArgumentException("Empty Item Filters OR");
                var expressions = new LinkedHashSet<String>();
                for (Tag entry : alternatives) expressions.add(filter((CompoundTag) entry, mappings));
                yield expressions.size() == 1 ? expressions.iterator().next() : "or(" + String.join("", expressions) + ")";
            }
            default -> {
                if (id.startsWith(LEGACY)) throw new IllegalArgumentException("Unsupported legacy filter " + id);
                if (mappings.stacks().contains(id)) throw new IllegalArgumentException("Component filter required for " + id);
                requireKeys(stack, Set.of("id", "Count"));
                yield "item(" + resource(mappings.items().contains(id) ? mappings.items().getString(id) : id) + ")";
            }
        };
    }

    private static void requireKeys(CompoundTag tag, Set<String> allowed) {
        if (!allowed.containsAll(tag.getAllKeys())) {
            throw new IllegalArgumentException("Filter has unsupported keys " + tag.getAllKeys());
        }
    }

    private static String resource(String value) {
        if (!RESOURCE_ID.matcher(value).matches()) throw new IllegalArgumentException("Invalid resource ID " + value);
        return value;
    }
}
