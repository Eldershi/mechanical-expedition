package expedition.stocktooltip.mixin;

import com.simibubi.create.content.logistics.BigItemStack;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Isolate tooltip callbacks from the exact stack used for logistics matching. */
@Mixin(targets = "com.simibubi.create.content.logistics.stockTicker.StockKeeperRequestScreen", remap = false)
abstract class StockKeeperTooltipMixin {
    @Redirect(method = "renderForeground(Lnet/minecraft/client/gui/GuiGraphics;IIF)V",
        at = @At(value = "FIELD",
            target = "Lcom/simibubi/create/content/logistics/BigItemStack;stack:Lnet/minecraft/world/item/ItemStack;"),
        require = 2, allow = 2)
    private ItemStack expedition$tooltipCopy(BigItemStack entry) {
        return entry.stack.copy();
    }
}
