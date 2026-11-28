package expedition.clientinterface.mixin;

import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.Font;
import net.minecraft.client.gui.GuiGraphics;
import net.minecraft.client.gui.screens.TitleScreen;
import net.minecraft.network.chat.Component;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyVariable;

@Mixin(GuiGraphics.class)
abstract class TitleButtonLabelMixin {
    @ModifyVariable(method = {
        "drawString(Lnet/minecraft/client/gui/Font;Lnet/minecraft/network/chat/Component;IIIZ)I",
        "drawCenteredString(Lnet/minecraft/client/gui/Font;Lnet/minecraft/network/chat/Component;III)V"
    },
        at = @At("HEAD"), argsOnly = true, ordinal = 1)
    private int expedition$centerAndesiteLabel(int y, Font font, Component text) {
        if (Minecraft.getInstance().screen instanceof TitleScreen && text != null) {
            String label = text.getString();
            if (label.equals("Realms") || label.equals("Mods")) {
                // Center the text on the raised face of the Andesite button.
                return y - 2;
            }
        }
        return y;
    }
}
