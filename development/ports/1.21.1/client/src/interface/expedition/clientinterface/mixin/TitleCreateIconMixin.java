package expedition.clientinterface.mixin;

import com.simibubi.create.infrastructure.gui.OpenCreateMenuButton;
import net.minecraft.client.Minecraft;
import net.minecraft.client.gui.screens.TitleScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.ModifyArg;

@Mixin(OpenCreateMenuButton.class)
abstract class TitleCreateIconMixin {
    @ModifyArg(method = "renderString", at = @At(value = "INVOKE",
        target = "Lnet/minecraft/client/gui/GuiGraphics;renderItem(Lnet/minecraft/world/item/ItemStack;II)V"),
        index = 2)
    private int expedition$centerGogglesOnButtonFace(int y) {
        return Minecraft.getInstance().screen instanceof TitleScreen ? y - 1 : y;
    }
}
