package expedition.spellcatalog.mixin;

import com.p1nero.iss_ponder.client.ClientPreviewController;
import com.p1nero.iss_ponder.client.PreviewProjection;
import expedition.spellcatalog.ExpeditionSpellCatalog;
import expedition.spellcatalog.MechanicalPonderStyle;
import expedition.spellcatalog.MechanicalSceneLayout;
import io.redspace.ironsspellbooks.api.spells.AbstractSpell;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.client.player.LocalPlayer;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Constant;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.ModifyConstant;
import org.spongepowered.asm.mixin.injection.Redirect;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import java.util.List;

/** Presentation only. Upstream input, casting, packets and session lifecycle stay authoritative. */
@Mixin(targets="com.p1nero.iss_ponder.client.SpellPreviewScreen", remap=false)
public abstract class SpellPreviewSkin extends Screen {
    @Shadow private AbstractSpell spell;
    @Shadow private boolean simulationAllowed;
    @Shadow private boolean playbackEnabled;
    @Shadow private double panelScroll;
    @Shadow private int panelContentHeight;
    @Shadow private int panelViewportHeight;
    @Shadow private long closingAt;
    @Shadow private void togglePlayback() {throw new AssertionError();}
    @Shadow private float transitionProgress() {throw new AssertionError();}
    @Shadow private List<?> buildStats(LocalPlayer player) { throw new AssertionError(); }
    @Shadow private void clampPanelScroll() { throw new AssertionError(); }
    @Shadow private void renderPanelContent(GuiGraphics g,int x,int w,int top,float opacity) { throw new AssertionError(); }
    @Shadow private void renderFooter(GuiGraphics g,int x,int w,int mx,int my,float opacity) { throw new AssertionError(); }
    protected SpellPreviewSkin() { super(null); }

    @Inject(method="mouseClicked",at=@At("HEAD"),cancellable=true)
    private void expedition$controls(double mx,double my,int button,CallbackInfoReturnable<Boolean> ci) {
        ci.setReturnValue(false);
        if(button!=0 || closingAt>=0)return;
        float slide = 1 - transitionProgress();
        int y = height - 46 + Math.round(slide * 14);
        if(MechanicalPonderStyle.hovered(mx,my,14,y,32,32)) {
            ExpeditionSpellCatalog.openIndex();ci.setReturnValue(true);return;
        }
        int panelWidth=Math.min(230,Math.max(128,Math.round(width*0.27F)));
        int x = width - panelWidth + 15 + Math.round(slide * 38);
        int close = width - 48;
        y = height - 48 + Math.round(slide * 15);
        if(MechanicalPonderStyle.hovered(mx,my,close,y,22,22)) {onClose();ci.setReturnValue(true);return;}
        if(simulationAllowed && MechanicalPonderStyle.hovered(mx,my,x,y,Math.max(40,close-x-7),22)) {
            togglePlayback();ci.setReturnValue(true);
        }
    }

    @Inject(method="panelWidth",at=@At("HEAD"),cancellable=true)
    private void expedition$narrowPanel(CallbackInfoReturnable<Integer> ci) {
        ci.setReturnValue(Math.min(230,Math.max(128,Math.round(width*0.27F))));
    }

    @Redirect(method="render",at=@At(value="INVOKE",
        target="Lnet/minecraft/client/gui/GuiGraphics;enableScissor(IIII)V"))
    private void expedition$noSceneScissor(GuiGraphics graphics,int l,int t,int r,int b) {}

    @Redirect(method="render",at=@At(value="INVOKE",
        target="Lnet/minecraft/client/gui/GuiGraphics;disableScissor()V"))
    private void expedition$noSceneScissorEnd(GuiGraphics graphics) {}

    @Redirect(method="render",at=@At(value="INVOKE",
        target="Lcom/p1nero/iss_ponder/client/PreviewProjection;render(Lnet/minecraft/client/gui/GuiGraphics;IIF)V"))
    private void expedition$fitCompleteScene(GuiGraphics graphics,int width,int height,float partialTick) {
        MechanicalSceneLayout.render(graphics,width,height,partialTick);
    }

    @Redirect(method="render",at=@At(value="INVOKE",
        target="Lnet/minecraft/client/gui/GuiGraphics;fill(IIIII)V"))
    private void expedition$noRectangularSceneFade(GuiGraphics graphics,int l,int t,int r,int b,int color) {}

    @ModifyConstant(method="render",constant=@Constant(intValue=0xB8050708))
    private int expedition$backgroundTop(int old) { return 0xEE20262C; }
    @ModifyConstant(method="render",constant=@Constant(intValue=0xD0090D0F))
    private int expedition$backgroundBottom(int old) { return 0xF0192026; }

    // The demonstration is deliberately borderless, as requested.
    @Inject(method="renderSceneFrame",at=@At("HEAD"),cancellable=true)
    private void expedition$noSceneFrame(GuiGraphics g,int l,int t,int r,int b,float opacity,CallbackInfo ci) {
        ci.cancel();
    }

    @Inject(method="renderHeader",at=@At("HEAD"),cancellable=true)
    private void expedition$header(GuiGraphics g,int panelX,int mx,int my,float opacity,CallbackInfo ci) {
        ci.cancel();
        if (spell==null || Minecraft.getInstance().player==null) return;
        int y=height-46+Math.round((1-opacity)*14);
        boolean hover=MechanicalPonderStyle.hovered(mx,my,14,y,32,32);
        MechanicalPonderStyle.button(g,font,14,y,32,32,"",true,hover,opacity);
        MechanicalPonderStyle.spellIcon(g,spell.getSpellIconResource(),18,y+4,24,opacity);
        String name=font.plainSubstrByWidth(spell.getDisplayName(Minecraft.getInstance().player).getString(),Math.max(30,panelX-68));
        g.drawString(font,name,54,y+6,MechanicalPonderStyle.alpha(0xFFF3EBD6,opacity),true);
        var school = spell.getSchoolType();
        String subtitle = hover ? MechanicalPonderStyle.text("gui.expedition_spell_catalog.index")
            : school == null ? MechanicalPonderStyle.text("gui.iss_ponder.unknown_school")
            : school.getDisplayName().getString();
        g.drawString(font,subtitle,54,y+20,MechanicalPonderStyle.alpha(0xFFB9C5B0,opacity),true);
    }

    @Inject(method="renderCameraHint",at=@At("HEAD"),cancellable=true)
    private void expedition$cameraHint(GuiGraphics g,int left,int right,int bottom,float opacity,CallbackInfo ci) {
        ci.cancel();
    }

    @Inject(method="renderPanel",at=@At("HEAD"),cancellable=true)
    private void expedition$parameters(GuiGraphics g,int panelX,int panelWidth,int mx,int my,float opacity,CallbackInfo ci) {
        ci.cancel();
        int right=width-14;
        int contentWidth=panelWidth-12;
        MechanicalPonderStyle.panel(g,panelX+2,14,Math.max(8,right-panelX-2),height-28,opacity);
        g.drawString(font,MechanicalPonderStyle.text("gui.expedition_spell_catalog.parameters"),panelX+15,26,
            MechanicalPonderStyle.alpha(MechanicalPonderStyle.INK,opacity),false);
        MechanicalPonderStyle.fill(g,panelX+15,41,right-12,42,MechanicalPonderStyle.BRASS,opacity);
        var lines=font.split(ClientPreviewController.getStatus(),contentWidth-44);
        int count=Math.max(1,lines.size());
        MechanicalPonderStyle.fill(g,panelX+15,52,panelX+18,52+count*10,MechanicalPonderStyle.GREEN,opacity);
        for(int i=0;i<count && i<lines.size();i++) g.drawString(font,lines.get(i),panelX+25,51+i*10,
            MechanicalPonderStyle.alpha(MechanicalPonderStyle.INK,opacity),false);
        int top=71+(count-1)*10;
        float progress=PreviewProjection.castProgress();
        if(progress>=0) {
            String value=Math.round(progress*100)+"%";int valueWidth=font.width(value);
            int barX=panelX+25,barRight=Math.max(barX+10,right-21-valueWidth),y=top-7;
            MechanicalPonderStyle.fill(g,barX,y,barRight,y+5,0xFF8E8062,opacity);
            MechanicalPonderStyle.fill(g,barX+1,y+1,barX+1+Math.round((barRight-barX-2)*progress),y+4,0xFF6E9163,opacity);
            g.drawString(font,value,right-16-valueWidth,y-2,MechanicalPonderStyle.alpha(MechanicalPonderStyle.INK,opacity),false);
            top+=9;
        }
        int bottom=Math.max(top+1,height-58);
        panelViewportHeight=Math.max(1,bottom-top);
        MechanicalPonderStyle.fill(g,panelX+9,top-5,right-8,bottom+3,0xFFF0E6CE,opacity);
        g.enableScissor(panelX+10,top-4,right-9,bottom+2);
        try { renderPanelContent(g,panelX,contentWidth,top,opacity); }
        finally { g.disableScissor(); }
        if(panelContentHeight>bottom-top) {
            int viewport=bottom-top,thumb=Math.max(12,viewport*viewport/panelContentHeight);
            int y=top+(int)Math.round((viewport-thumb)*panelScroll/Math.max(1,panelContentHeight-panelViewportHeight));
            int x=right-8;
            MechanicalPonderStyle.fill(g,x-1,top,x+2,bottom,0xFFB2A482,opacity);
            MechanicalPonderStyle.fill(g,x-1,y,x+2,y+thumb,0xFF777E6B,opacity);
            MechanicalPonderStyle.fill(g,x-1,y,x,y+thumb,0xFFD7DDC8,opacity);
        }
        // Upstream suppresses the footer while the modal browser is open.
        if(mx>-1000) renderFooter(g,panelX,panelWidth,mx,my,opacity);
    }

    @Inject(method="renderPanelContent",at=@At("HEAD"),cancellable=true)
    private void expedition$readableStats(GuiGraphics g,int panelX,int panelWidth,int top,float opacity,CallbackInfo ci) {
        ci.cancel();
        LocalPlayer player=Minecraft.getInstance().player;
        if(spell==null || player==null) {panelContentHeight=0;return;}
        int x=panelX+17,maxWidth=panelWidth-34,y=top-(int)panelScroll,logical=0;
        Component description=Component.literal(Component.translatable(spell.getComponentId()+".guide").getString());
        for(var line:font.split(description,maxWidth)) {
            g.drawString(font,line,x,y+logical,MechanicalPonderStyle.alpha(MechanicalPonderStyle.MUTED,opacity),false);
            logical+=11;
        }
        logical+=10;
        MechanicalPonderStyle.fill(g,x,y+logical,x+maxWidth,y+logical+1,MechanicalPonderStyle.BRASS,opacity);
        logical+=9;
        g.drawString(font,MechanicalPonderStyle.text("gui.expedition_spell_catalog.data"),x,y+logical,
            MechanicalPonderStyle.alpha(MechanicalPonderStyle.INK,opacity),false);
        logical+=16;
        int row=0;
        for(Object object:buildStats(player)) {
            SpellStatAccess stat=(SpellStatAccess)object;
            String label=stat.expedition$label().getString(),value=stat.expedition$value().getString();
            int labelWidth=font.width(label),valueWidth=font.width(value);
            int height=labelWidth+valueWidth+14<=maxWidth?14:
                15+font.split(Component.literal(value),maxWidth-8).size()*10;
            if((row++&1)==0) MechanicalPonderStyle.fill(g,x-3,y+logical-3,x+maxWidth+3,y+logical+height-3,0xFFE4D8BC,opacity);
            g.drawString(font,label,x,y+logical,MechanicalPonderStyle.alpha(MechanicalPonderStyle.MUTED,opacity),false);
            int ink=label.equals("+")?MechanicalPonderStyle.GREEN:MechanicalPonderStyle.INK;
            if(labelWidth+valueWidth+14<=maxWidth) {
                g.drawString(font,value,x+maxWidth-valueWidth,y+logical,MechanicalPonderStyle.alpha(ink,opacity),false);
                logical+=14;
            } else {
                logical+=11;
                for(var line:font.split(Component.literal(value),maxWidth-8)) {
                    g.drawString(font,line,x+8,y+logical,MechanicalPonderStyle.alpha(ink,opacity),false);
                    logical+=10;
                }
                logical+=4;
            }
        }
        panelContentHeight=logical+5;clampPanelScroll();
    }

    @Inject(method="renderFooter",at=@At("HEAD"),cancellable=true)
    private void expedition$buttons(GuiGraphics g,int panelX,int panelWidth,int mx,int my,float opacity,CallbackInfo ci) {
        ci.cancel();
        int y=height-48+Math.round((1-opacity)*15),x=panelX+15,close=width-48,w=Math.max(40,close-x-7);
        MechanicalPonderStyle.button(g,font,x,y,w,22,
            MechanicalPonderStyle.text(playbackEnabled?"gui.iss_ponder.pause":"gui.iss_ponder.play"),
            simulationAllowed,MechanicalPonderStyle.hovered(mx,my,x,y,w,22),opacity);
        MechanicalPonderStyle.button(g,font,close,y,22,22,"X",true,
            MechanicalPonderStyle.hovered(mx,my,close,y,22,22),opacity);
    }
}
