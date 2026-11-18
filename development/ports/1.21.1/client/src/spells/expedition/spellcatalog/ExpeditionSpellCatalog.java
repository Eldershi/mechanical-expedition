package expedition.spellcatalog;

import com.p1nero.iss_ponder.client.ClientPreviewController;
import com.p1nero.iss_ponder.client.SpellPreviewScreen;
import com.p1nero.iss_ponder.network.ModNetwork;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import net.createmod.catnip.gui.ScreenOpener;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.network.ConnectionProtocol;
import net.minecraft.network.chat.Component;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.client.event.ClientTickEvent;
import net.neoforged.neoforge.client.event.ScreenEvent;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.network.registration.NetworkRegistry;

@Mod(value = "expedition_spell_catalog", dist = Dist.CLIENT)
public final class ExpeditionSpellCatalog {
    private static Screen previewParent;
    private static Screen reopenOnTick;

    public ExpeditionSpellCatalog() {
        NeoForge.EVENT_BUS.addListener(this::returnFromPreview);
        NeoForge.EVENT_BUS.addListener(this::tick);
    }

    public static void openIndex() {
        SpellPonderCatalog.refreshIfChanged();
        ScreenOpener.open(null, new SpellSchoolIndexScreen());
    }

    public static void preview(AbstractSpell spell) {
        Minecraft client = Minecraft.getInstance();
        if (client.player == null || !spell.isEnabled() || ClientPreviewController.isPending()) return;
        var payload = new ModNetwork.StartPreview(spell.getSpellResource(), spell.getMinLevel());
        if (client.getConnection() == null || !NetworkRegistry.hasChannel(
                client.getConnection().getConnection(), ConnectionProtocol.PLAY, payload.type().id())) {
            client.player.displayClientMessage(Component.translatable("expedition.spells.preview_unavailable"), false);
            return;
        }
        previewParent = client.screen;
        ClientPreviewController.request(spell.getSpellResource(), spell.getMinLevel());
    }

    private void returnFromPreview(ScreenEvent.Closing event) {
        if (!(event.getScreen() instanceof SpellPreviewScreen)) return;
        reopenOnTick = previewParent;
        previewParent = null;
    }

    private void tick(ClientTickEvent.Post event) {
        SpellPonderCatalog.tick();
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
