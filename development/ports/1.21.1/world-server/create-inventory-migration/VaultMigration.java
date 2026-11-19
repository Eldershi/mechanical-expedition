package expedition.migration;

import com.google.gson.GsonBuilder;
import com.google.gson.JsonParser;
import com.mojang.datafixers.DataFixer;
import com.mojang.serialization.Dynamic;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;
import java.util.regex.Pattern;
import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.StringTag;
import net.minecraft.nbt.Tag;
import net.minecraft.util.datafix.DataFixers;
import net.minecraft.util.datafix.fixes.References;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.chunk.storage.RegionFile;
import net.minecraft.world.level.chunk.storage.RegionStorageInfo;

public final class VaultMigration {
    private static final int SOURCE_VERSION = 3465;
    private static final int TARGET_VERSION = 3955;
    private static final int CHUNKS_PER_SIDE = 32;
    private static final Pattern REGION_NAME = Pattern.compile("r\\.(-?\\d+)\\.(-?\\d+)\\.mca");
    private static final Pattern EXTERNAL_CHUNK_NAME = Pattern.compile("c\\.-?\\d+\\.-?\\d+\\.mcc");
    private static final Set<String> LEGACY_STACK_FIELDS = Set.of("id", "Count", "tag", "Slot", "ForgeCaps");
    private static final Map<String, String> PLAIN_ITEM_REPLACEMENTS = Map.of(
        "thermal:copper_nugget", "create:copper_nugget",
        "cmi:quartz_ore", "minecraft:nether_quartz_ore",
        "cmi:deepslate_quartz_ore", "minecraft:nether_quartz_ore",
        "cmi:peat", "minecraft:charcoal",
        "cmi:peat_block", "immersiveengineering:coal_coke",
        "cmi:enriched_silicon", "cmi:single_crystal_silicon"
    );
    private static final RegionStorageInfo REGION_INFO = new RegionStorageInfo("expedition-copy", Level.OVERWORLD, "chunk");

    private final DataFixer fixer = DataFixers.getDataFixer();
    private final Set<String> targetItems;
    private final Set<String> targetEnchantments;
    private final ListTag recovered = new ListTag();
    private final ListTag retainedWithWarnings = new ListTag();
    private final Map<String, Long> counts = new TreeMap<>();
    private final Map<String, Long> recoveredItems = new TreeMap<>();
    private final Map<String, Long> recoveredReasons = new TreeMap<>();
    private final Map<String, Long> enchantmentWarnings = new TreeMap<>();
    private final Map<String, Long> renamedItems = new TreeMap<>();
    private final Map<CompoundTag, CompoundTag> convertedStacks = new LinkedHashMap<>();

    private VaultMigration(Set<String> targetItems, Set<String> targetEnchantments) {
        this.targetItems = targetItems;
        this.targetEnchantments = targetEnchantments;
    }

    public static void main(String[] args) throws IOException {
        SharedConstants.tryDetectVersion();
        if (SharedConstants.getCurrentVersion().getDataVersion().getVersion() != TARGET_VERSION) {
            throw new IllegalArgumentException("The migration requires Minecraft 1.21.1 data fixers");
        }
        Set<String> targetItems = new HashSet<>();
        Set<String> targetEnchantments = null;
        try (var registry = Files.newBufferedReader(Path.of(args[1]))) {
            var document = JsonParser.parseReader(registry).getAsJsonObject();
            document.getAsJsonArray("items").forEach(item -> targetItems.add(item.getAsString()));
            if (document.has("enchantments")) {
                targetEnchantments = new HashSet<>();
                for (var value : document.getAsJsonArray("enchantments")) {
                    targetEnchantments.add(value.getAsString());
                }
            }
        }
        if (!targetItems.contains("minecraft:air")) {
            throw new IllegalArgumentException("Expected the target server's exported item registry");
        }
        new VaultMigration(targetItems, targetEnchantments).copyRegions(Path.of(args[0]), Path.of(args[2]));
    }

    private void copyRegions(Path source, Path output) throws IOException {
        Path regionOutput = Files.createDirectory(output.resolve("region"));
        List<Path> files;
        try (var entries = Files.list(source)) {
            files = entries.sorted().toList();
        }
        List<Path> regions = files.stream().filter(file -> REGION_NAME.matcher(file.getFileName().toString()).matches())
            .toList();
        if (regions.isEmpty()) throw new IllegalArgumentException("No Anvil region files in " + source);
        for (Path file : files) {
            String name = file.getFileName().toString();
            if (REGION_NAME.matcher(name).matches() || EXTERNAL_CHUNK_NAME.matcher(name).matches()) {
                Files.copy(file, regionOutput.resolve(name));
            }
        }
        for (Path region : regions) migrateRegion(regionOutput.resolve(region.getFileName()), regionOutput);

        CompoundTag recovery = new CompoundTag();
        recovery.putInt("SourceDataVersion", SOURCE_VERSION);
        recovery.putInt("TargetDataVersion", TARGET_VERSION);
        recovery.put("Stacks", recovered);
        recovery.put("RetainedWithWarnings", retainedWithWarnings);
        NbtIo.writeCompressed(recovery, output.resolve("unconverted-stacks.nbt"));
        String report = new GsonBuilder().setPrettyPrinting().create().toJson(Map.of(
            "counts", counts, "recoveredItems", recoveredItems, "recoveredReasons", recoveredReasons,
            "enchantmentWarnings", enchantmentWarnings, "renamedItems", renamedItems));
        Files.writeString(output.resolve("migration-summary.json"), report + "\n");
        System.out.println(report);
    }

    private void migrateRegion(Path file, Path directory) throws IOException {
        var name = REGION_NAME.matcher(file.getFileName().toString());
        if (!name.matches()) throw new IllegalArgumentException("Invalid region name " + file);
        int startX = Integer.parseInt(name.group(1)) * CHUNKS_PER_SIDE;
        int startZ = Integer.parseInt(name.group(2)) * CHUNKS_PER_SIDE;
        try (var region = new RegionFile(REGION_INFO, file, directory, false)) {
            for (int z = startZ; z < startZ + CHUNKS_PER_SIDE; z++) {
                for (int x = startX; x < startX + CHUNKS_PER_SIDE; x++) {
                    var position = new ChunkPos(x, z);
                    if (!region.hasChunk(position)) continue;
                    CompoundTag chunk;
                    try (var input = region.getChunkDataInputStream(position)) {
                        if (input == null) throw new IOException("Unreadable chunk " + position + " in " + file);
                        chunk = NbtIo.read(input, NbtAccounter.unlimitedHeap());
                    }
                    if (!migrateChunk(chunk)) continue;
                    try (var stream = region.getChunkDataOutputStream(position)) {
                        NbtIo.write(chunk, stream);
                    }
                }
            }
        }
    }

    private boolean migrateChunk(CompoundTag chunk) {
        boolean changed = false;
        int version = chunk.getInt("DataVersion");
        for (Tag tag : chunk.getList("block_entities", Tag.TAG_COMPOUND)) {
            CompoundTag block = (CompoundTag) tag;
            if (!block.getString("id").equals("create:item_vault")) {
                if (version == SOURCE_VERSION) changed |= migrateBlockFilters(block);
                continue;
            }
            CompoundTag inventory = block.getCompound("Inventory");
            ListTag items = inventory.getList("Items", Tag.TAG_COMPOUND);
            add(counts, "vaults", 1);
            if (items.isEmpty()) continue;
            add(counts, "filledVaults", 1);
            if (version == TARGET_VERSION) continue;
            if (version != SOURCE_VERSION) {
                throw new IllegalArgumentException("Unsupported vault chunk DataVersion " + version);
            }
            ListTag converted = new ListTag();
            Set<Integer> occupied = new HashSet<>();
            for (Tag item : items) {
                CompoundTag stack = (CompoundTag) item;
                if (stack.contains("Slot", Tag.TAG_ANY_NUMERIC) && !occupied.add(stack.getInt("Slot"))) {
                    throw new IllegalArgumentException("Duplicate vault slot at " + block.getInt("x") + ", "
                        + block.getInt("y") + ", " + block.getInt("z"));
                }
                CompoundTag result = migrateStack(block, inventory.getInt("Size"), stack);
                if (result != null) converted.add(result);
            }
            if (!items.equals(converted)) {
                inventory.put("Items", converted);
                changed = true;
            }
        }
        if (changed) add(counts, "changedChunks", 1);
        return changed;
    }

    private boolean migrateBlockFilters(CompoundTag block) {
        if (block.getString("id").equals("create:funnel")) {
            CompoundTag old = block.getCompound("Filter");
            CompoundTag updated = migrateFilter(block, old, "Filter");
            if (updated == old) return false;
            block.put("Filter", updated);
            return true;
        }
        if (!block.getString("id").equals("create:stock_ticker")) return false;
        ListTag categories = block.getList("Categories", Tag.TAG_COMPOUND);
        boolean changed = false;
        for (int index = 0; index < categories.size(); index++) {
            CompoundTag old = categories.getCompound(index);
            CompoundTag updated = migrateFilter(block, old, "Categories[" + index + "]");
            if (updated == old) continue;
            categories.set(index, updated);
            changed = true;
        }
        return changed;
    }

    private CompoundTag migrateFilter(CompoundTag block, CompoundTag old, String field) {
        if (!LegacyCreateFilters.hasLegacySettings(old)) return old;
        CompoundTag updated = convertFilter(old);
        if (updated != null) {
            add(counts, "convertedBlockFilters", 1);
            return updated;
        }
        CompoundTag entry = recoveryEntry(block, old, "unverified_filter_payload");
        entry.putString("Field", field);
        recovered.add(entry);
        add(counts, "unconvertedBlockFilters", 1);
        return old;
    }

    private CompoundTag convertFilter(CompoundTag old) {
        CompoundTag upgraded = LegacyCreateFilters.convert(old, this::fixFilterPayload);
        return upgraded != null && registeredStack(upgraded) ? upgraded : null;
    }

    private CompoundTag fixFilterPayload(CompoundTag old) {
        int count = old.getInt("Count");
        if (count < 1 || count > 99 || !LEGACY_STACK_FIELDS.containsAll(old.getAllKeys())
            || old.contains("ForgeCaps") && (!old.contains("ForgeCaps", Tag.TAG_COMPOUND)
                || !old.getCompound("ForgeCaps").isEmpty())
            || old.contains("tag") && !old.getString("id").startsWith("minecraft:")
                && !Set.of("display").containsAll(old.getCompound("tag").getAllKeys())) return null;
        CompoundTag payload = old.copy();
        payload.remove("ForgeCaps");
        CompoundTag upgraded = fixPayload(payload);
        return upgraded != null && registeredStack(upgraded) ? upgraded : null;
    }

    private CompoundTag migrateStack(CompoundTag block, int size, CompoundTag original) {
        if (original.contains("count", Tag.TAG_INT) && !original.contains("Count")) {
            return original;
        }
        String id = original.getString("id");
        int count = original.getInt("Count");
        add(counts, "legacySlots", 1);
        add(counts, "legacyItems", Math.max(0, count));
        if (!original.contains("Slot", Tag.TAG_ANY_NUMERIC) || original.getInt("Slot") < 0
            || original.getInt("Slot") >= size || !original.contains("Count", Tag.TAG_ANY_NUMERIC)
            || count < 1 || count > 99 || id.isEmpty() || id.equals("minecraft:air")) {
            return recover(block, original, "invalid_slot_or_stack");
        }
        String migratedId = migratedItemId(original);
        if (!targetItems.contains(migratedId) && !id.startsWith("minecraft:")) {
            return recover(block, original, "missing_item_id");
        }
        if (LegacyCreateFilters.hasLegacySettings(original)) {
            CompoundTag filter = convertFilter(original);
            if (filter == null) return recover(block, original, "unverified_filter_payload");
            filter.put("Slot", original.get("Slot").copy());
            add(counts, "convertedSlots", 1);
            add(counts, "convertedItems", count);
            archiveEnchantmentRisks(block, original, filter);
            return filter;
        }
        if (!LEGACY_STACK_FIELDS.containsAll(original.getAllKeys())
            || original.contains("ForgeCaps") && (!original.contains("ForgeCaps", Tag.TAG_COMPOUND)
                || !original.getCompound("ForgeCaps").isEmpty())
            || original.contains("tag") && (!original.contains("tag", Tag.TAG_COMPOUND)
                || !id.startsWith("minecraft:") && !original.getCompound("tag").isEmpty())) {
            return recover(block, original, "unverified_mod_payload");
        }
        CompoundTag payload = original.copy();
        payload.remove("Slot");
        payload.remove("ForgeCaps");
        payload.putString("id", migratedId);
        CompoundTag result = convertedStacks.get(payload);
        if (result == null) {
            CompoundTag upgraded = fixPayload(payload);
            if (upgraded == null) {
                return recover(block, original, "unexpected_datafixer_result");
            }
            if (!targetItems.contains(upgraded.getString("id"))) {
                return recover(block, original, "missing_item_id");
            }
            if (!availableNestedItems(upgraded.getCompound("components"))) {
                return recover(block, original, "missing_nested_item_id");
            }
            result = upgraded;
            if (convertedStacks.size() == 16_384) convertedStacks.clear();
            convertedStacks.put(payload, result);
        }
        CompoundTag withSlot = result.copy();
        withSlot.put("Slot", original.get("Slot"));
        add(counts, "convertedSlots", 1);
        add(counts, "convertedItems", count);
        String upgradedId = withSlot.getString("id");
        if (!id.equals(upgradedId)) add(renamedItems, id + " -> " + upgradedId, count);
        archiveEnchantmentRisks(block, original, withSlot);
        return withSlot;
    }

    private String migratedItemId(CompoundTag original) {
        String id = original.getString("id");
        String replacement = PLAIN_ITEM_REPLACEMENTS.get(id);
        if (replacement == null || targetItems.contains(id)
            || !LEGACY_STACK_FIELDS.containsAll(original.getAllKeys())
            || original.contains("tag") && (!original.contains("tag", Tag.TAG_COMPOUND)
                || !original.getCompound("tag").isEmpty())
            || original.contains("ForgeCaps") && (!original.contains("ForgeCaps", Tag.TAG_COMPOUND)
                || !original.getCompound("ForgeCaps").isEmpty())) {
            return id;
        }
        return replacement;
    }

    private void archiveEnchantmentRisks(CompoundTag block, CompoundTag original, CompoundTag upgraded) {
        Set<String> risks = new TreeSet<>();
        collectEnchantmentRisks(upgraded, risks);
        if (risks.isEmpty()) return;
        CompoundTag entry = recoveryEntry(block, original, targetEnchantments == null
            ? "unverified_enchantment_registry" : "missing_enchantment_ids");
        ListTag ids = new ListTag();
        for (String id : risks) {
            ids.add(StringTag.valueOf(id));
            add(enchantmentWarnings, id, 1);
        }
        entry.put("EnchantmentIds", ids);
        retainedWithWarnings.add(entry);
        add(counts, "retainedSlotsWithEnchantmentWarnings", 1);
    }

    private void collectEnchantmentRisks(CompoundTag stack, Set<String> risks) {
        CompoundTag components = stack.getCompound("components");
        for (String id : List.of("minecraft:enchantments", "minecraft:stored_enchantments")) {
            CompoundTag enchantment = components.getCompound(id);
            CompoundTag levels = enchantment.contains("levels", Tag.TAG_COMPOUND)
                ? enchantment.getCompound("levels") : enchantment;
            for (String enchantmentId : levels.getAllKeys()) {
                if (enchantmentId.equals("show_in_tooltip")) continue;
                if (targetEnchantments == null || !targetEnchantments.contains(enchantmentId)) {
                    risks.add(enchantmentId);
                }
            }
        }
        for (CompoundTag nested : nestedItems(components)) collectEnchantmentRisks(nested, risks);
    }

    CompoundTag fixPayload(CompoundTag payload) {
        Tag fixed = fixer.update(References.ITEM_STACK, new Dynamic<Tag>(NbtOps.INSTANCE, payload),
                                 SOURCE_VERSION, TARGET_VERSION).getValue();
        if (!(fixed instanceof CompoundTag upgraded) || upgraded.getInt("count") != payload.getInt("Count")
            || upgraded.contains("Count") || upgraded.contains("tag")) {
            return null;
        }
        return upgraded;
    }

    boolean registeredStack(CompoundTag stack) {
        return targetItems.contains(stack.getString("id"))
            && availableNestedItems(stack.getCompound("components"));
    }

    private boolean availableNestedItems(CompoundTag components) {
        return nestedItems(components).stream().allMatch(this::registeredStack);
    }

    private static List<CompoundTag> nestedItems(CompoundTag components) {
        List<CompoundTag> nested = new ArrayList<>();
        for (String key : List.of("minecraft:container", "create:filter_items")) {
            for (Tag slot : components.getList(key, Tag.TAG_COMPOUND)) {
                nested.add(((CompoundTag) slot).getCompound("item"));
            }
        }
        for (String key : List.of("minecraft:bundle_contents", "minecraft:charged_projectiles")) {
            for (Tag item : components.getList(key, Tag.TAG_COMPOUND)) {
                nested.add((CompoundTag) item);
            }
        }
        return nested;
    }

    private static CompoundTag recoveryEntry(CompoundTag block, CompoundTag original, String reason) {
        CompoundTag entry = new CompoundTag();
        entry.putIntArray("BlockPos", new int[]{block.getInt("x"), block.getInt("y"), block.getInt("z")});
        entry.putString("BlockEntity", block.getString("id"));
        entry.putString("Reason", reason);
        entry.put("OriginalStack", original.copy());
        return entry;
    }

    private CompoundTag recover(CompoundTag block, CompoundTag original, String reason) {
        recovered.add(recoveryEntry(block, original, reason));
        add(counts, "recoveredSlots", 1);
        add(counts, "recoveredItems", Math.max(0, original.getInt("Count")));
        add(recoveredItems, original.getString("id"), Math.max(0, original.getInt("Count")));
        add(recoveredReasons, reason, 1);
        return null;
    }

    private static void add(Map<String, Long> counter, String key, long delta) {
        counter.merge(key, delta, Long::sum);
    }
}
