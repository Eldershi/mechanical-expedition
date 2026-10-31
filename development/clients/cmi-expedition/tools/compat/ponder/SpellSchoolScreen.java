package expedition.ponderui;

import com.mojang.blaze3d.systems.RenderSystem;
import com.p1nero.iss_ponder.client.ClientPreviewController;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import net.createmod.ponder.foundation.PonderTag;
import net.createmod.ponder.foundation.ui.PonderTagScreen;
import net.createmod.ponder.foundation.ui.PonderButton;
import net.createmod.ponder.enums.PonderGuiTextures;
import net.createmod.catnip.layout.LayoutHelper;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.world.item.ItemStack;
import java.util.*;

/** The second index level uses Ponder navigation, buttons and pagination. */
public final class SpellSchoolScreen extends PonderTagScreen {
    private int page,pageSize;
    private final List<PonderButton> spellButtons=new ArrayList<>();
    public SpellSchoolScreen(PonderTag tag) {super(tag);}
    public int spellPage() {return page;}
    public int spellPageSize() {return pageSize;}
    public List<PonderButton> spellButtons() {return List.copyOf(spellButtons);}
    @Override protected void m_7856_() {
        super.m_7856_();spellButtons.clear();
        var entry=SpellPonderCatalog.school(getTag().getId());
        int columns=Math.max(1,Math.min(11,(f_96543_-56)/36));
        int maxRows=Math.max(1,Math.min(3,(f_96544_-50-getItemsY())/36));
        pageSize=columns*maxRows;
        int pages=Math.max(1,(entry.spells().size()+pageSize-1)/pageSize);page=Math.min(page,pages-1);
        int start=page*pageSize;
        int count=Math.min(pageSize,entry.spells().size()-start);
        int rows=Math.max(1,(count+columns-1)/columns);
        // Exact PonderTagScreen item layout: 28px cells, 8px spacing, 20px buttons inset 4px.
        var layout=LayoutHelper.centeredHorizontal(count,rows,28,28,8);
        itemArea=layout.getArea();
        for(int i=start;i<Math.min(entry.spells().size(),start+pageSize);i++) {
            AbstractSpell spell=entry.spells().get(i);
            var button=new SpellButton(f_96543_/2+layout.getX()+4,getItemsY()+layout.getY()+4,spell);
            button.withCallback(()->ClientPreviewController.request(spell.getSpellResource(),1));
            spellButtons.add(button);m_142416_(button);layout.next();
        }
        if(pages>1) {
            var prev=new PonderButton(f_96543_/2-60,f_96544_-32);
            prev.showing(ItemStack.f_41583_);
            prev.showing(PonderGuiTextures.ICON_PONDER_LEFT);prev.setActive(page>0);
            prev.withCallback(()->{page--;m_232761_();});m_142416_(prev);
            var next=new PonderButton(f_96543_/2+40,f_96544_-32);
            next.showing(ItemStack.f_41583_);
            next.showing(PonderGuiTextures.ICON_PONDER_RIGHT);next.setActive(page+1<pages);
            next.withCallback(()->{page++;m_232761_();});m_142416_(next);
        }
    }
    @Override protected void renderWindow(GuiGraphics g,int mx,int my,float partialTick) {
        super.renderWindow(g,mx,my,partialTick);
        var entry=SpellPonderCatalog.school(getTag().getId());
        int pages=Math.max(1,(entry.spells().size()+Math.max(1,pageSize)-1)/Math.max(1,pageSize));
        if(pages>1)g.m_280137_(f_96547_,(page+1)+" / "+pages,f_96543_/2,f_96544_-26,0xFFE5E7DB);
    }
    @Override protected void renderWindowForeground(GuiGraphics g,int mx,int my,float partialTick) {
        super.renderWindowForeground(g,mx,my,partialTick);
        // Like native item tooltips, render names in the foreground, above 420z buttons.
        for(var button:spellButtons)if(MechanicalPonderStyle.hovered(mx,my,button.m_252754_(),button.m_252907_(),20,20)) {
            var pose=g.m_280168_();pose.m_85836_();pose.m_252880_(0,0,200);
            g.m_280666_(f_96547_,button.getToolTip(),mx,my);pose.m_85849_();break;
        }
    }
    private static final class SpellButton extends PonderButton {
        private final AbstractSpell spell;
        SpellButton(int x,int y,AbstractSpell spell) {
            super(x,y);this.spell=spell;
            showing(ItemStack.f_41583_);
            showing((g,ix,iy)->MechanicalPonderStyle.spellIcon(g,spell.getSpellIconResource(),ix,iy,16,1));
            toolTip=List.of(Component.m_237113_(spell.getDisplayName(Minecraft.m_91087_().f_91074_).getString()));
        }
        @Override protected void renderTooltip(GuiGraphics g,int mx,int my,float partialTick) {}
    }
}
