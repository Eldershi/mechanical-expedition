import dev.ftb.mods.ftblibrary.snbt.SNBT;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.regex.Pattern;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;

final class ConvertItemFilters {
    private static final String LEGACY = "itemfilters:";
    private static final String SMART_FILTER = "ftbfiltersystem:smart_filter";
    private static final String FILTER_COMPONENT = "ftbfiltersystem:filter";
    private static final Pattern RESOURCE_ID = Pattern.compile("[a-z0-9_.-]+:[a-z0-9_.\\-/]+");

    private record ConvertedFile(Path relative, CompoundTag contents, int count) {}

    public static void main(String[] args) throws IOException {
        if (args.length != 2) {
            throw new IllegalArgumentException("Usage: ConvertItemFilters <quest source> <new output directory>");
        }
        Path source = Path.of(args[0]).toRealPath();
        Path output = Path.of(args[1]).toAbsolutePath().normalize();
        if (!Files.isDirectory(source) || Files.exists(output) || output.startsWith(source)) {
            throw new IllegalArgumentException("Use an existing source directory and a separate new output directory");
        }

        var converted = new ArrayList<ConvertedFile>();
        try (var files = Files.walk(source)) {
            for (Path file : files.filter(Files::isRegularFile).filter(path -> path.toString().endsWith(".snbt")).sorted().toList()) {
                if (!Files.readString(file).contains(LEGACY)) continue;
                try {
                    CompoundTag contents = SNBT.read(file);
                    if (contents == null) throw new IllegalArgumentException("Could not read SNBT");
                    int count = convert(contents);
                    if (count > 0) converted.add(new ConvertedFile(source.relativize(file), contents, count));
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
                converted.stream().mapToInt(ConvertedFile::count).sum(), converted.size());
    }

    private static int convert(Tag node) {
        int converted = 0;
        if (node instanceof CompoundTag tag) {
            if (tag.getString("id").startsWith(LEGACY)) {
                String expression = filter(tag);
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
            for (String key : tag.getAllKeys()) converted += convert(tag.get(key));
        } else if (node instanceof ListTag list) {
            for (Tag entry : list) converted += convert(entry);
        }
        return converted;
    }

    private static String filter(CompoundTag stack) {
        String id = stack.getString("id");
        CompoundTag settings = stack.getCompound("tag");
        return switch (id) {
            case "itemfilters:tag" -> {
                requireKeys(stack, Set.of("id", "Count", "tag"));
                requireKeys(settings, Set.of("value"));
                String value = resource(settings.getString("value"));
                if (value.startsWith("forge:")) value = "c:" + value.substring("forge:".length());
                yield "item_tag(" + value + ")";
            }
            case "itemfilters:or" -> {
                requireKeys(stack, Set.of("id", "Count", "tag"));
                requireKeys(settings, Set.of("items"));
                ListTag alternatives = settings.getList("items", Tag.TAG_COMPOUND);
                if (alternatives.isEmpty()) throw new IllegalArgumentException("Empty Item Filters OR");
                var expressions = new ArrayList<String>();
                for (Tag entry : alternatives) expressions.add(filter((CompoundTag) entry));
                yield "or(" + String.join("", expressions) + ")";
            }
            default -> {
                if (id.startsWith(LEGACY)) throw new IllegalArgumentException("Unsupported legacy filter " + id);
                requireKeys(stack, Set.of("id", "Count"));
                yield "item(" + resource(id) + ")";
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
