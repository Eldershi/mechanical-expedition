package expedition.spellcatalog;

import com.p1nero.iss_ponder.client.ClientPreviewController;
import com.p1nero.iss_ponder.client.SpellPreviewScreen;
import com.p1nero.iss_ponder.network.ModNetwork;
import io.redspace.ironsspellbooks.api.registry.SpellRegistry;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import io.redspace.ironsspellbooks.api.spells.SchoolType;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.createmod.ponder.foundation.ui.PonderIndexScreen;
import net.createmod.ponder.foundation.ui.PonderTagIndexScreen;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.components.Button;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.chat.Component;
import net.minecraft.network.ConnectionProtocol;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;
import net.minecraft.resources.ResourceLocation;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.network.registration.NetworkRegistry;

@Mod(value = "expedition_spell_catalog", dist = Dist.CLIENT)
public final class ExpeditionSpellCatalog {
    private static final ResourceLocation UNKNOWN_SCHOOL =
        ResourceLocation.fromNamespaceAndPath("expedition_spell_catalog", "unknown");
    private Screen previewParent;
    private Screen reopenOnTick;

    public ExpeditionSpellCatalog() {
        NeoForge.EVENT_BUS.addListener(this::addCatalog);
        NeoForge.EVENT_BUS.addListener(this::returnFromPreview);
        NeoForge.EVENT_BUS.addListener(this::updatePreviewNavigation);
    }

    private void addCatalog(ScreenEvent.Init.Post event) {
        Screen parent = event.getScreen();
        if (!(parent instanceof PonderIndexScreen) && !(parent instanceof PonderTagIndexScreen)) return;
        Minecraft client = Minecraft.getInstance();
        if (client.player == null) return;
        event.addListener(Button.builder(Component.translatable("expedition.spells.title"),
            button -> openSchools(client, parent)).bounds(parent.width - 123, 6, 117, 20).build());
    }

    private void openSchools(Minecraft client, Screen parent) {
        Map<ResourceLocation, List<AbstractSpell>> groups = new LinkedHashMap<>();
        for (AbstractSpell spell : SpellRegistry.getEnabledSpells()) {
            if (spell == SpellRegistry.none()) continue;
            SchoolType school = spell.getSchoolType();
            ResourceLocation id = school == null ? UNKNOWN_SCHOOL : school.getId();
            groups.computeIfAbsent(id, key -> new ArrayList<>()).add(spell);
        }
        List<ChoiceScreen.Option> options = groups.entrySet().stream().map(group -> {
            List<AbstractSpell> spells = List.copyOf(group.getValue());
            SchoolType school = spells.getFirst().getSchoolType();
            Component title = school == null ? Component.translatable("expedition.spells.other")
                : school.getDisplayName();
            return new ChoiceScreen.Option(Component.translatable("expedition.spells.school", title, spells.size()),
                group.getKey().toString(), () -> openSpells(client, client.screen, title, spells));
        }).toList();
        client.setScreen(new ChoiceScreen(parent, Component.translatable("expedition.spells.title"), options));
    }

    private void openSpells(Minecraft client, Screen parent, Component title, List<AbstractSpell> spells) {
        List<ChoiceScreen.Option> options = spells.stream().map(spell -> new ChoiceScreen.Option(
            Component.translatable(spell.getComponentId()), spell.getSpellResource().toString(),
            () -> preview(client, spell))).toList();
        client.setScreen(new ChoiceScreen(parent, title, options));
    }

    private void preview(Minecraft client, AbstractSpell spell) {
        if (client.player == null || !spell.isEnabled() || ClientPreviewController.isPending()) return;
        int level = spell.getMinLevel();
        CustomPacketPayload payload = new ModNetwork.StartPreview(spell.getSpellResource(), level);
        if (client.getConnection() != null && NetworkRegistry.hasChannel(
            client.getConnection().getConnection(), ConnectionProtocol.PLAY, payload.type().id())) {
            previewParent = client.screen;
            ClientPreviewController.request(spell.getSpellResource(), level);
            return;
        }
        client.player.displayClientMessage(Component.translatable("expedition.spells.preview_unavailable"), false);
    }

    private void returnFromPreview(ScreenEvent.Closing event) {
        if (!(event.getScreen() instanceof SpellPreviewScreen)) return;
        reopenOnTick = previewParent;
        previewParent = null;
    }

    private void updatePreviewNavigation(ClientTickEvent.Post event) {
        Minecraft client = Minecraft.getInstance();
        if (reopenOnTick != null) {
            Screen previous = reopenOnTick;
            reopenOnTick = null;
            if (client.screen == null && client.player != null) client.setScreen(previous);
        }
        if (previewParent != null && !ClientPreviewController.isPending()
            && !(client.screen instanceof SpellPreviewScreen)) {
            previewParent = null;
        }
    }
}
