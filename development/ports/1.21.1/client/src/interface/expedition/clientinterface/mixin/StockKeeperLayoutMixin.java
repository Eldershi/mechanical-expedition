package expedition.clientinterface.mixin;

import expedition.clientinterface.StockKeeperBounds;


import com.simibubi.create.content.logistics.stockTicker.StockKeeperRequestMenu;
import com.simibubi.create.content.logistics.stockTicker.StockKeeperRequestScreen;
import com.simibubi.create.foundation.gui.menu.AbstractSimiContainerScreen;
import com.simibubi.create.foundation.gui.widget.IconButton;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.client.renderer.Rect2i;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = StockKeeperRequestScreen.class, priority = 900, remap = false)
abstract class StockKeeperLayoutMixin extends AbstractSimiContainerScreen<StockKeeperRequestMenu>
        implements StockKeeperBounds {
    @Shadow int windowWidth;
    @Shadow int windowHeight;
    @Shadow boolean encodeRequester;

    protected StockKeeperLayoutMixin(StockKeeperRequestMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
    }

    @Inject(method = "init", at = @At("TAIL"), order = 1100)
    private void expedition$alignRequestControls(CallbackInfo callback) {
        int bottom = topPos + windowHeight;
        for (var child : children()) {
            if (!(child instanceof IconButton button)) {
                continue;
            }
            // Cyber Goggles puts the request-mode control partly on the Send/Pin row.
            if (button.getX() == leftPos + windowWidth - 29 && button.getY() == bottom - 21) {
                button.setX(leftPos + 49);
                button.setY(bottom - 20);
            } else if (button.getX() == leftPos + 24 && button.getY() == bottom - 26) {
                button.setY(bottom - 20);
            }
        }
    }

    @Override
    public int expedition$ordersButtonX() {
        int right = leftPos + windowWidth;
        // Leave the bookmarks column to the left and the main panel below the fallback.
        return right + 22 <= width ? right + 4 : right - 20;
    }

    @Override
    public int expedition$ordersButtonY() {
        return leftPos + windowWidth + 22 <= width ? topPos + 24 : topPos + 2;
    }

    @Inject(method = "getExtraAreas", at = @At("RETURN"), cancellable = true, order = 1100)
    private void expedition$reserveProductionButton(CallbackInfoReturnable<List<Rect2i>> callback) {
        int x = expedition$ordersButtonX();
        if (!encodeRequester && x >= leftPos + windowWidth) {
            var extraAreas = new ArrayList<>(callback.getReturnValue());
            extraAreas.add(new Rect2i(x, expedition$ordersButtonY(), 18, 18));
            callback.setReturnValue(extraAreas);
        }
    }
}
