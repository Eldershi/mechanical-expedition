package expedition.clientinterface.mixin;

import expedition.clientinterface.StockKeeperBounds;
import com.simibubi.create.content.logistics.stockTicker.StockKeeperRequestMenu;
import com.simibubi.create.content.logistics.stockTicker.StockKeeperRequestScreen;
import com.simibubi.create.foundation.gui.menu.AbstractSimiContainerScreen;
import com.simibubi.create.foundation.gui.widget.IconButton;
import java.util.List;
import net.minecraft.client.renderer.Rect2i;
import net.minecraft.network.chat.Component;
import net.minecraft.world.entity.player.Inventory;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = StockKeeperRequestScreen.class, priority = 900, remap = false)
abstract class StockKeeperLayoutMixin extends AbstractSimiContainerScreen<StockKeeperRequestMenu>
        implements StockKeeperBounds {
    @Shadow int windowWidth;
    @Shadow int windowHeight;
    @Shadow boolean encodeRequester;
    @Shadow private List<Rect2i> extraAreas;

    protected StockKeeperLayoutMixin(StockKeeperRequestMenu menu, Inventory inventory, Component title) {
        super(menu, inventory, title);
    }

    @Inject(method = "init", at = @At("TAIL"), order = 1100)
    private void expedition$alignRequestControls(CallbackInfo callback) {
        int ordersX = expedition$ordersButtonX();
        if (!encodeRequester && ordersX >= leftPos + windowWidth) {
            extraAreas.add(new Rect2i(ordersX, expedition$ordersButtonY(), 18, 18));
        }
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
}
