package expedition.spellcatalog;

import com.mojang.blaze3d.systems.RenderSystem;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;

/** Code-drawn casework; buttons use the active pack's ordinary GUI sprite. */
public final class MechanicalPonderStyle {
    public static final int INK = 0xFF39382F;
    public static final int MUTED = 0xFF74674E;
    public static final int BRASS = 0xFF947447;
    public static final int GREEN = 0xFF4C7656;
    public static final int PAPER = 0xFFE5D8BB;
    private static final ResourceLocation BUTTON = ResourceLocation.withDefaultNamespace("widget/button");
    private static final ResourceLocation BUTTON_HIGHLIGHTED =
        ResourceLocation.withDefaultNamespace("widget/button_highlighted");
    private static final ResourceLocation BUTTON_DISABLED =
        ResourceLocation.withDefaultNamespace("widget/button_disabled");

    private MechanicalPonderStyle() {}

    public static int alpha(int color, float opacity) {
        return color & 0xFFFFFF | Math.round((color >>> 24) * Math.max(0, Math.min(1, opacity))) << 24;
    }

    public static boolean hovered(double mx, double my, int x, int y, int w, int h) {
        return mx >= x && mx < x + w && my >= y && my < y + h;
    }

    public static void fill(GuiGraphics graphics, int x, int y, int right, int bottom, int color, float opacity) {
        graphics.fill(x,y,right,bottom,alpha(color,opacity));
    }

    public static void frame(GuiGraphics g, int x, int y, int w, int h, float opacity) {
        fill(g,x,y,x+w,y+1,0xFF35372F,opacity);
        fill(g,x,y+h-1,x+w,y+h,0xFF35372F,opacity);
        fill(g,x,y+1,x+1,y+h-1,0xFF35372F,opacity);
        fill(g,x+w-1,y+1,x+w,y+h-1,0xFF35372F,opacity);
        fill(g,x+1,y+1,x+w-1,y+3,0xFFD4C69B,opacity);
        fill(g,x+1,y+3,x+3,y+h-1,0xFFB69A6D,opacity);
        fill(g,x+3,y+h-3,x+w-1,y+h-1,0xFF70583D,opacity);
        fill(g,x+w-3,y+3,x+w-1,y+h-3,0xFF8F724D,opacity);
        for (int sx : new int[]{x+6,x+w-7}) for (int sy : new int[]{y+7,y+h-8}) {
            fill(g,sx-1,sy-2,sx+2,sy+3,0xFF686B65,opacity);
            fill(g,sx-2,sy-1,sx+3,sy+2,0xFF686B65,opacity);
            fill(g,sx-1,sy-1,sx+2,sy+1,0xFFD0D0BC,opacity);
            fill(g,sx-1,sy,sx+2,sy+1,0xFF50534D,opacity);
        }
    }

    public static void panel(GuiGraphics g, int x, int y, int w, int h, float opacity) {
        fill(g,x+1,y+1,x+w-1,y+h-1,PAPER,opacity);
        for (int line=y+4; line<y+h-4; line+=3)
            fill(g,x+3,line,x+w-3,line+1,0xFFECE1C7,opacity*0.55F);
        frame(g,x,y,w,h,opacity);
    }

    public static void button(GuiGraphics g, Font font, int x, int y, int w, int h,
                              String label, boolean enabled, boolean hovered, float opacity) {
        ResourceLocation sprite = enabled ? (hovered ? BUTTON_HIGHLIGHTED : BUTTON) : BUTTON_DISABLED;
        RenderSystem.enableBlend();
        g.setColor(1,1,1,opacity);
        g.blitSprite(sprite, x, y, w, h);
        g.setColor(1,1,1,1);
        if (!label.isEmpty()) g.drawCenteredString(font,label,x+w/2,y+(h-8)/2,
            alpha(enabled ? 0xFFF5F2E7 : 0xFFA5A39A,opacity));
    }

    public static String text(String key) { return Component.translatable(key).getString(); }

    public static void spellIcon(GuiGraphics g,ResourceLocation texture,int x,int y,int size,float opacity) {
        RenderSystem.enableBlend();g.setColor(1,1,1,opacity);
        g.blit(texture,x,y,size,size,0,0,16,16,16,16);
        g.setColor(1,1,1,1);
        // A single pixel entirely inside the icon, preserving the native bitmap.
        fill(g,x,y,x+size,y+1,0xFF555B50,opacity);
        fill(g,x,y+size-1,x+size,y+size,0xFF555B50,opacity);
        fill(g,x,y+1,x+1,y+size-1,0xFF555B50,opacity);
        fill(g,x+size-1,y+1,x+size,y+size-1,0xFF555B50,opacity);
    }

}
