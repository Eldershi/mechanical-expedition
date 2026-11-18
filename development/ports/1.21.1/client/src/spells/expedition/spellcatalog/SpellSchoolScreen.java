package expedition.spellcatalog;

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
    private final SpellPonderCatalog.SchoolEntry entry;
    private int page,pageSize;
    private final List<PonderButton> spellButtons=new ArrayList<>();
    public SpellSchoolScreen(PonderTag tag, SpellPonderCatalog.SchoolEntry entry) {
        super(tag);
        this.entry = entry;
    }
    public int spellPage() {return page;}
    public int spellPageSize() {return pageSize;}
    public List<PonderButton> spellButtons() {return List.copyOf(spellButtons);}
    @Override protected void init() {
        super.init();spellButtons.clear();
        int columns=Math.max(1,Math.min(11,(width-56)/36));
        int maxRows=Math.max(1,Math.min(3,(height-50-getItemsY())/36));
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
            var button=new SpellButton(width/2+layout.getX()+4,getItemsY()+layout.getY()+4,spell);
            button.withCallback(()->ExpeditionSpellCatalog.preview(spell));
            spellButtons.add(button);addRenderableWidget(button);layout.next();
        }
        if(pages>1) {
            var prev=new PonderButton(width/2-60,height-32);
            prev.showing(ItemStack.EMPTY);
            prev.showing(PonderGuiTextures.ICON_PONDER_LEFT);prev.setActive(page>0);
            prev.withCallback(()->{page--;rebuildWidgets();});addRenderableWidget(prev);
            var next=new PonderButton(width/2+40,height-32);
            next.showing(ItemStack.EMPTY);
            next.showing(PonderGuiTextures.ICON_PONDER_RIGHT);next.setActive(page+1<pages);
            next.withCallback(()->{page++;rebuildWidgets();});addRenderableWidget(next);
        }
    }
    @Override protected void renderWindow(GuiGraphics g,int mx,int my,float partialTick) {
        super.renderWindow(g,mx,my,partialTick);
        int pages=Math.max(1,(entry.spells().size()+Math.max(1,pageSize)-1)/Math.max(1,pageSize));
        if(pages>1)g.drawCenteredString(font,(page+1)+" / "+pages,width/2,height-26,0xFFE5E7DB);
    }
    @Override protected void renderWindowForeground(GuiGraphics g,int mx,int my,float partialTick) {
        super.renderWindowForeground(g,mx,my,partialTick);
        // Like native item tooltips, render names in the foreground, above 420z buttons.
        for(var button:spellButtons)if(MechanicalPonderStyle.hovered(mx,my,button.getX(),button.getY(),20,20)) {
            var pose=g.pose();pose.pushPose();pose.translate(0,0,200);
            g.renderComponentTooltip(font,button.getToolTip(),mx,my);pose.popPose();break;
        }
    }
    private static final class SpellButton extends PonderButton {
        SpellButton(int x,int y,AbstractSpell spell) {
            super(x,y);
            showing(ItemStack.EMPTY);
            showing((g,ix,iy)->MechanicalPonderStyle.spellIcon(g,spell.getSpellIconResource(),ix,iy,16,1));
            toolTip=List.of(Component.literal(spell.getDisplayName(Minecraft.getInstance().player).getString()));
        }
        @Override protected void renderTooltip(GuiGraphics g,int mx,int my,float partialTick) {}
    }
}
