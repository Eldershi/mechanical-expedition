package expedition.ponderui;

import net.createmod.catnip.layout.PaginationState;
import net.createmod.ponder.foundation.ui.PonderTagIndexScreen;
import java.util.*;

/** A focused view of the same school tags also listed in the global Ponder index. */
public final class SpellSchoolIndexScreen extends PonderTagIndexScreen {
    @Override protected void m_7856_() {
        super.m_7856_();
        if(pageNext!=null)removeWidgets(pageNext);
        if(pagePrev!=null)removeWidgets(pagePrev);
        pageNext=null;pagePrev=null;
        sortedModTags=List.of(Map.entry("iss_ponder",SpellPonderCatalog.tags()));
        paginationState=new PaginationState(false,1,1);
        setupModTagEntries();
    }
}
