package expedition.ponderui;

import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.registries.ItemRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.ISpellContainer;
import expedition.ponderui.mixin.PonderTagIconAccess;
import net.createmod.ponder.api.registration.PonderPlugin;
import net.createmod.ponder.api.registration.PonderTagRegistrationHelper;
import net.createmod.ponder.foundation.PonderIndex;
import net.createmod.ponder.foundation.PonderTag;
import net.createmod.ponder.foundation.registration.DefaultPonderTagRegistrationHelper;
import net.createmod.ponder.foundation.registration.PonderTagRegistry;
import net.createmod.ponder.foundation.registration.PonderLocalization;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.client.Minecraft;
import java.util.*;

/** Real Ponder categories backed by the enabled spell registry, including add-ons. */
public final class SpellPonderCatalog implements PonderPlugin {
    public record SchoolEntry(ResourceLocation tagId,String title,List<AbstractSpell> spells) {}
    private static final Map<ResourceLocation,SchoolEntry> SCHOOLS=new LinkedHashMap<>();
    private static String signature="";
    private static int refreshTicks;
    public String getModId() {return "iss_ponder";}
    public static SchoolEntry school(ResourceLocation id) {return SCHOOLS.get(id);}
    public static List<SchoolEntry> schools() {return List.copyOf(SCHOOLS.values());}
    public static List<PonderTag> tags() {
        return SCHOOLS.keySet().stream().map(id->PonderIndex.getTagAccess().getRegisteredTag(id)).filter(Objects::nonNull).toList();
    }
    private static String fingerprint() {
        return SpellRegistry.getEnabledSpells().stream().filter(spell->spell!=null && spell!=SpellRegistry.none())
            .map(spell->spell.getSpellResource()+"@"+(spell.getSchoolType()==null?"unknown":spell.getSchoolType().getId()))
            .sorted().reduce("",(a,b)->a+";"+b);
    }
    public static void refreshAfterConfigSync() {
        if(Minecraft.m_91087_().f_91074_==null || ++refreshTicks%20!=0)return;
        if(!fingerprint().equals(signature)) {
            var registry=(PonderTagRegistry)PonderIndex.getTagAccess();
            var previous=new HashSet<>(SCHOOLS.keySet());
            registry.getListedTags().removeIf(tag->previous.contains(tag.getId()));
            // Refresh only our categories. Some installed plugins cannot register scenes twice.
            new SpellPonderCatalog().registerTags(new DefaultPonderTagRegistrationHelper("iss_ponder",registry,
                (PonderLocalization)PonderIndex.getLangAccess()));
        }
    }
    @Override public void registerTags(PonderTagRegistrationHelper<ResourceLocation> helper) {
        SCHOOLS.clear();
        // Spell school/config lookups have fallback values before the login sync.
        if(Minecraft.m_91087_().f_91074_==null) {signature="";return;}
        Map<String,List<AbstractSpell>> grouped=new TreeMap<>();
        for(AbstractSpell spell:SpellRegistry.getEnabledSpells()) {
            if(spell==null || spell==SpellRegistry.none())continue;
            String key=spell.getSchoolType()==null?"iss_ponder:unknown":spell.getSchoolType().getId().toString();
            grouped.computeIfAbsent(key,ignored->new ArrayList<>()).add(spell);
        }
        for(var group:grouped.entrySet()) {
            var spells=group.getValue();spells.sort(Comparator.comparing(spell->spell.getSpellResource().toString()));
            var school=spells.get(0).getSchoolType();
            String title=school==null?Component.m_237115_("gui.iss_ponder.unknown_school").getString():school.getDisplayName().getString();
            var key=new ResourceLocation(group.getKey());
            var id=new ResourceLocation("iss_ponder","school/"+key.m_135827_()+"/"+key.m_135815_());
            SCHOOLS.put(id,new SchoolEntry(id,title,List.copyOf(spells)));
            helper.registerTag(id).title(title)
                .description(Component.m_237110_("gui.expedition_ponder_ui.school_description",spells.size()).getString())
                .item(ItemRegistry.SCROLL.get(),true,false).addToIndex().register();
            // Empty scrolls all use the same model. A real spell container selects the
            // scroll model supplied by this school, including add-on schools.
            var tag=PonderIndex.getTagAccess().getRegisteredTag(id);
            ISpellContainer.createScrollContainer(spells.get(0),1,((PonderTagIconAccess)tag).expedition$itemIcon());
        }
        signature=fingerprint();
    }
}
