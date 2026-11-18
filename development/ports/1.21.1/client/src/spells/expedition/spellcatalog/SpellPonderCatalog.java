package expedition.spellcatalog;

import expedition.spellcatalog.mixin.PonderTagIconAccess;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import io.redspace.ironsspellbooks.registries.ItemRegistry;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.TreeMap;
import net.createmod.ponder.api.registration.PonderPlugin;
import net.createmod.ponder.api.registration.PonderTagRegistrationHelper;
import net.createmod.ponder.foundation.PonderIndex;
import net.createmod.ponder.foundation.PonderTag;
import net.createmod.ponder.foundation.registration.DefaultPonderTagRegistrationHelper;
import net.createmod.ponder.foundation.registration.PonderLocalization;
import net.createmod.ponder.foundation.registration.PonderTagRegistry;
import net.minecraft.client.Minecraft;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;

/** Adds native Ponder categories for all enabled spell schools, including add-ons. */
public final class SpellPonderCatalog implements PonderPlugin {
    private static final String CATEGORY_OWNER = "iss_ponder";
    private static final ResourceLocation UNKNOWN_SCHOOL =
        ResourceLocation.fromNamespaceAndPath(CATEGORY_OWNER, "unknown");
    private static final Map<ResourceLocation, SchoolEntry> SCHOOLS = new LinkedHashMap<>();
    private static List<AbstractSpell> indexed = List.of();
    private static int refreshTicks;

    public record SchoolEntry(Component title, List<AbstractSpell> spells) {}

    @Override
    public String getModId() {
        return CATEGORY_OWNER;
    }

    public static SchoolEntry school(ResourceLocation id) {
        return SCHOOLS.get(id);
    }

    static List<PonderTag> tags() {
        return SCHOOLS.keySet().stream().map(PonderIndex.getTagAccess()::getRegisteredTag)
            .filter(Objects::nonNull).toList();
    }

    static void tick() {
        if (++refreshTicks % 20 == 0) refreshIfChanged();
    }

    static void refreshIfChanged() {
        if (Minecraft.getInstance().player == null) return;
        var enabled = enabledSpells();
        if (enabled.equals(indexed)) return;

        // Login applies server spell config after the initial Ponder registration.
        var registry = (PonderTagRegistry) PonderIndex.getTagAccess();
        registry.getListedTags().removeIf(tag -> SCHOOLS.containsKey(tag.getId()));
        var helper = new DefaultPonderTagRegistrationHelper(CATEGORY_OWNER, registry,
            (PonderLocalization) PonderIndex.getLangAccess());
        registerSchools(helper, enabled);
    }

    @Override
    public void registerTags(PonderTagRegistrationHelper<ResourceLocation> helper) {
        // Before login Iron's server-side spell config has yet to be applied.
        var enabled = Minecraft.getInstance().player == null ? List.<AbstractSpell>of() : enabledSpells();
        registerSchools(helper, enabled);
    }

    private static List<AbstractSpell> enabledSpells() {
        return SpellRegistry.getEnabledSpells().stream()
            .filter(spell -> spell != null && spell != SpellRegistry.none())
            .sorted(Comparator.comparing(AbstractSpell::getSpellResource))
            .toList();
    }

    private static void registerSchools(PonderTagRegistrationHelper<ResourceLocation> helper,
                                        List<AbstractSpell> enabled) {
        SCHOOLS.clear();
        Map<ResourceLocation, List<AbstractSpell>> grouped = new TreeMap<>();
        for (AbstractSpell spell : enabled) {
            var school = spell.getSchoolType();
            var id = school == null ? UNKNOWN_SCHOOL : school.getId();
            grouped.computeIfAbsent(id, ignored -> new ArrayList<>()).add(spell);
        }
        grouped.forEach((schoolId, spells) -> {
            var sample = spells.getFirst();
            var school = sample.getSchoolType();
            var title = school == null ? Component.translatable("gui.iss_ponder.unknown_school") : school.getDisplayName();
            var id = ResourceLocation.fromNamespaceAndPath(CATEGORY_OWNER,
                "school/" + schoolId.getNamespace() + "/" + schoolId.getPath());
            var entry = new SchoolEntry(title, List.copyOf(spells));
            SCHOOLS.put(id, entry);
            helper.registerTag(id).title(title.getString()).description(description(entry).getString())
                .item(ItemRegistry.SCROLL.get(), true, false).addToIndex().register();
            var tag = (PonderTagIconAccess) PonderIndex.getTagAccess().getRegisteredTag(id);
            ISpellContainer.createScrollContainer(sample, sample.getMinLevel(), tag.expedition$itemIcon());
        });
        indexed = enabled;
    }

    public static Component description(SchoolEntry entry) {
        return Component.translatable("gui.expedition_spell_catalog.school_description", entry.spells().size());
    }
}
