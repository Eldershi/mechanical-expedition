package expedition.clientinterface.mixin;

import expedition.clientinterface.StockKeeperBounds;


import net.minecraft.client.Minecraft;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(targets = "io.github.nbcss.createfactorycontroller.content.gui.screen.ProductionOrdersScreen", remap = false)
abstract class ProductionOrdersButtonMixin {
    @Inject(method = "gutterButtonX", at = @At("HEAD"), cancellable = true)
    private static void expedition$placeOrdersButtonX(int original, CallbackInfoReturnable<Integer> callback) {
        if (Minecraft.getInstance().screen instanceof StockKeeperBounds stockKeeper) {
            callback.setReturnValue(stockKeeper.expedition$ordersButtonX());
        }
    }

    @Inject(method = "gutterButtonY", at = @At("HEAD"), cancellable = true)
    private static void expedition$placeOrdersButtonY(int original, CallbackInfoReturnable<Integer> callback) {
        if (Minecraft.getInstance().screen instanceof StockKeeperBounds stockKeeper) {
            callback.setReturnValue(stockKeeper.expedition$ordersButtonY());
        }
    }
}
