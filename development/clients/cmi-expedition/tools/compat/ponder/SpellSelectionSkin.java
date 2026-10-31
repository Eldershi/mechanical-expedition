package expedition.ponderui.mixin;

import expedition.ponderui.MechanicalPonderStyle;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.network.chat.Component;
import io.redspace.ironsspellbooks.api.spells.SchoolType;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets="com.p1nero.iss_ponder.client.SpellSelectionMenu",remap=false)
public abstract class SpellSelectionSkin {
    @Shadow private boolean visible;
    @Shadow private float transitionProgress() {throw new AssertionError();}

    @ModifyConstant(method="*",constant=@Constant(intValue=0xFFD6B46A))
    private int expedition$title(int old) {return 0xFF624D31;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFF77623B))
    private int expedition$border(int old) {return 0xFF8D7452;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFFE9E2D2))
    private int expedition$ink(int old) {return MechanicalPonderStyle.INK;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFFAEB4B1))
    private int expedition$muted(int old) {return MechanicalPonderStyle.MUTED;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFF62A99B))
    private int expedition$accent(int old) {return MechanicalPonderStyle.GREEN;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFA0B1012))
    private int expedition$paper(int old) {return 0xFFF0E6CC;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFF151C1D))
    private int expedition$search(int old) {return 0xFFFCF6E8;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xD9101517))
    private int expedition$list(int old) {return 0xFFE2D5B8;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFF223631))
    private int expedition$selected(int old) {return 0xFFBDCAA9;}
    @ModifyConstant(method="*",constant=@Constant(intValue=0xFF1D2827))
    private int expedition$hover(int old) {return 0xFFD6DDC4;}

    @Inject(method="drawButton",at=@At("HEAD"),cancellable=true)
    private void expedition$buttons(GuiGraphics g,Font font,int x,int y,int w,int h,
                                    Component label,boolean enabled,boolean hovered,float opacity,CallbackInfo ci) {
        MechanicalPonderStyle.button(g,font,x,y,w,h,label.getString(),enabled,hovered,opacity);
        ci.cancel();
    }

    @Inject(method="schoolColor",at=@At("RETURN"),cancellable=true)
    private static void expedition$schoolInk(SchoolType school,CallbackInfoReturnable<Integer> ci) {
        ci.setReturnValue(MechanicalPonderStyle.schoolInk(ci.getReturnValue()));
    }

    // School names carry explicit white/gold formatting from their translations.
    // Let the dark school palette control their ink on the paper background.
    @ModifyArg(method="renderRows",at=@At(value="INVOKE",
        target="Lnet/minecraft/client/gui/GuiGraphics;m_280614_(Lnet/minecraft/client/gui/Font;Lnet/minecraft/network/chat/Component;IIIZ)I"),index=1)
    private Component expedition$plainRowText(Component text) {
        return Component.m_237113_(text.getString());
    }

    @Inject(method="render",at=@At("TAIL"))
    private void expedition$casework(GuiGraphics g,Font font,int sw,int sh,int mx,int my,CallbackInfo ci) {
        if(!visible)return;
        float progress=transitionProgress();
        int w=Math.max(230,Math.min(390,sw-24)),h=Math.max(150,Math.min(236,sh-20));
        MechanicalPonderStyle.frame(g,(sw-w)/2,(sh-h)/2+Math.round((1-progress)*12),w,h,progress);
    }
}
