package expedition.migration;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.function.UnaryOperator;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;

final class LegacyCreateFilters {
    private static final Set<String> LIST_FIELDS = Set.of("Items", "Blacklist", "RespectNBT", "display");
    private static final Set<String> ATTRIBUTE_FIELDS = Set.of("MatchedAttributes", "WhitelistMode", "display");
    private static final Set<String> IN_TAG_FIELDS = Set.of("attributeId", "tag", "Inverted");
    static final String LEGACY_COPPER_NUGGET = "thermal:copper_nugget";
    static final String COPPER_NUGGET = "create:copper_nugget";
    private static final List<String> MODES = List.of("whitelist_disj", "whitelist_conj", "blacklist");
    private static final int LIST_CAPACITY = 18;

    private LegacyCreateFilters() {}

    static boolean hasLegacySettings(CompoundTag stack) {
        return stack.contains("Count", Tag.TAG_ANY_NUMERIC) && stack.contains("tag", Tag.TAG_COMPOUND)
            && (stack.getString("id").equals("create:filter") || stack.getString("id").equals("create:attribute_filter"));
    }

    static CompoundTag convert(CompoundTag original, UnaryOperator<CompoundTag> fixStack) {
        CompoundTag legacy = original.getCompound("tag");
        CompoundTag custom = switch (original.getString("id")) {
            case "create:filter" -> listComponents(legacy, fixStack);
            case "create:attribute_filter" -> attributeComponents(legacy);
            default -> null;
        };
        if (custom == null) return null;

        CompoundTag payload = original.copy();
        payload.remove("tag");
        if (legacy.contains("display")) {
            if (!legacy.contains("display", Tag.TAG_COMPOUND)) return null;
            CompoundTag display = new CompoundTag();
            display.put("display", legacy.getCompound("display").copy());
            payload.put("tag", display);
        }
        CompoundTag updated = fixStack.apply(payload);
        if (updated == null) return null;
        CompoundTag result = updated.copy();
        CompoundTag components = result.getCompound("components");
        components.merge(custom);
        if (!components.isEmpty()) result.put("components", components);
        return result;
    }

    private static CompoundTag listComponents(CompoundTag legacy, UnaryOperator<CompoundTag> fixStack) {
        if (!LIST_FIELDS.containsAll(legacy.getAllKeys())) return null;
        CompoundTag contents = legacy.getCompound("Items");
        if (!Set.of("Size", "Items").containsAll(contents.getAllKeys())
            || (legacy.contains("Items") && !legacy.contains("Items", Tag.TAG_COMPOUND))
            || (contents.contains("Items") && !contents.contains("Items", Tag.TAG_LIST))) return null;

        ListTag items = new ListTag();
        Set<Integer> occupied = new HashSet<>();
        for (Tag value : contents.getList("Items", Tag.TAG_COMPOUND)) {
            CompoundTag oldItem = (CompoundTag) value;
            int slot = oldItem.getInt("Slot");
            if (!oldItem.contains("Slot", Tag.TAG_ANY_NUMERIC) || slot < 0 || slot >= LIST_CAPACITY
                || !occupied.add(slot)) return null;
            CompoundTag payload = oldItem.copy();
            payload.remove("Slot");
            CompoundTag item = convertFilterMember(payload, legacy.getBoolean("RespectNBT"), fixStack);
            if (item == null) return null;
            CompoundTag entry = new CompoundTag();
            entry.putInt("slot", slot);
            entry.put("item", item);
            items.add(entry);
        }
        CompoundTag converted = new CompoundTag();
        if (!items.isEmpty()) converted.put("create:filter_items", items);
        if (legacy.contains("Blacklist")) converted.putBoolean("create:filter_items_blacklist", legacy.getBoolean("Blacklist"));
        if (legacy.contains("RespectNBT")) converted.putBoolean("create:filter_items_respect_nbt", legacy.getBoolean("RespectNBT"));
        return converted;
    }

    private static CompoundTag convertFilterMember(CompoundTag item, boolean respectData, UnaryOperator<CompoundTag> fixStack) {
        if (hasLegacySettings(item)) return convert(item, fixStack);
        String id = item.getString("id");
        CompoundTag metadata = item.getCompound("tag");
        if (id.equals(LEGACY_COPPER_NUGGET) && (!item.contains("tag") || metadata.isEmpty())
            && !respectData) {
            item.putString("id", COPPER_NUGGET);
        } else if (id.equals("create:belt_connector") && !respectData
            && metadata.getAllKeys().equals(Set.of("FirstPulley"))
            && metadata.getCompound("FirstPulley").getAllKeys().equals(Set.of("X", "Y", "Z"))) {
            item.remove("tag");
        } else if (id.startsWith("create:cardboard_package_")
            && metadata.getAllKeys().equals(Set.of("Items")) && metadata.contains("Items", Tag.TAG_COMPOUND)
            && metadata.getCompound("Items").isEmpty()) {
            item.remove("tag");
        }
        return fixStack.apply(item);
    }

    private static CompoundTag attributeComponents(CompoundTag legacy) {
        if (!ATTRIBUTE_FIELDS.containsAll(legacy.getAllKeys())
            || (legacy.contains("MatchedAttributes") && !legacy.contains("MatchedAttributes", Tag.TAG_LIST))) return null;
        int mode = legacy.getInt("WhitelistMode");
        if (mode < 0 || mode >= MODES.size()) return null;
        ListTag attributes = new ListTag();
        for (Tag value : legacy.getList("MatchedAttributes", Tag.TAG_COMPOUND)) {
            CompoundTag oldAttribute = (CompoundTag) value;
            if (!IN_TAG_FIELDS.containsAll(oldAttribute.getAllKeys())
                || !oldAttribute.getString("attributeId").equals("create:in_tag")) return null;
            ResourceLocation tag = ResourceLocation.tryParse(oldAttribute.getString("tag"));
            if (tag == null || oldAttribute.getString("tag").isEmpty()) return null;
            CompoundTag attribute = new CompoundTag();
            attribute.putString("type", "create:in_tag");
            attribute.putString("value", tag.toString());
            CompoundTag entry = new CompoundTag();
            entry.put("attribute", attribute);
            entry.putBoolean("inverted", oldAttribute.getBoolean("Inverted"));
            attributes.add(entry);
        }
        CompoundTag converted = new CompoundTag();
        converted.putString("create:attribute_filter_whitelist_mode", MODES.get(mode));
        if (!attributes.isEmpty()) converted.put("create:attribute_filter_matched_attributes", attributes);
        return converted;
    }
}
