package expedition.storage.mixin;

import com.simibubi.create.content.logistics.BigItemStack;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Redirect;

/** Isolate tooltip callbacks from the exact stack used for logistics matching. */
@Mixin(targets = "com.simibubi.create.content.logistics.stockTicker.StockKeeperRequestScreen", remap = false)
public abstract class StockKeeperTooltipMixin {
    @Redirect(method = "renderForeground", at = @At(value = "FIELD",
            target = "Lcom/simibubi/create/content/logistics/BigItemStack;stack:Lnet/minecraft/world/item/ItemStack;"),
            require = 2, allow = 2, remap = false)
    private ItemStack expedition$tooltipCopy(BigItemStack entry) {
        // Apotheosis may add affix/socket attribute UUIDs while making a tooltip.
        // Never let presentation change the stock snapshot or selected order.
        return entry.stack.m_41777_();
    }
}
