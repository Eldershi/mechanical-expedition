package expedition.clientinterface.mixin;

import net.blay09.mods.trashslot.TrashSlotSaveState;
import net.blay09.mods.trashslot.api.IGuiContainerLayout;
import net.blay09.mods.trashslot.client.ContainerSettings;
import net.minecraft.client.gui.screens.inventory.AbstractContainerScreen;
import net.minecraft.client.gui.screens.inventory.InventoryScreen;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

@Mixin(value = TrashSlotSaveState.class, remap = false)
abstract class TrashSlotDefaultsMixin {
    @Inject(method = "lambda$getSettings$0", at = @At("RETURN"))
    private static void expedition$showOnPersonalStorage(IGuiContainerLayout layout,
        AbstractContainerScreen<?> screen, String containerId, CallbackInfoReturnable<ContainerSettings> callback) {
        if (screen instanceof InventoryScreen
                || containerId.equals("top/theillusivec4/curios/client/gui/CuriosScreen")
                || containerId.startsWith("sophisticated_backpack_")) {
            callback.getReturnValue().setEnabled(true);
        }
    }
}
