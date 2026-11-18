package expedition.spellcatalog.mixin;

import expedition.spellcatalog.SpellPonderCatalog;
import expedition.spellcatalog.SpellSchoolScreen;
import net.createmod.ponder.foundation.PonderTag;
import net.createmod.ponder.foundation.ui.PonderTagScreen;
import net.createmod.ponder.foundation.ui.PonderTagIndexScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;

@Mixin(value=PonderTagIndexScreen.class,remap=false)
public abstract class SpellPonderTagNavigation {
    @Redirect(method="lambda$setupModTagEntries$4",at=@At(value="NEW",
        target="net/createmod/ponder/foundation/ui/PonderTagScreen"))
    private PonderTagScreen expedition$schoolPage(PonderTag tag) {
        var school = SpellPonderCatalog.school(tag.getId());
        return school == null ? new PonderTagScreen(tag) : new SpellSchoolScreen(tag, school);
    }
}
