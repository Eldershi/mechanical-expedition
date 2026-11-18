package expedition.storage.mixin;

import com.buuz135.functionalstorage.block.tile.ControllableDrawerTile;
import com.buuz135.functionalstorage.item.StorageUpgradeItem;
import com.hrznstudio.titanium.component.inventory.InventoryComponent;
import net.minecraft.world.item.ItemStack;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Shadow;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

@Mixin(value = ControllableDrawerTile.class, remap = false)
public abstract class DrawerUpgradeFilterMixin {
    @Shadow
    public abstract InventoryComponent<?> getStorageUpgrades();

    @Inject(method = "<init>", at = @At("RETURN"))
    private void expedition$limitMixedStorageTiers(CallbackInfo info) {
        var upgrades = getStorageUpgrades();
        var existingFilter = upgrades.getInsertPredicate();
        upgrades.setInputFilter((candidate, slot) -> {
            if (!existingFilter.test(candidate, slot)) {
                return false;
            }
            if (!(candidate.getItem() instanceof StorageUpgradeItem)) {
                return true;
            }
            for (int i = 0; i < upgrades.getSlots(); i++) {
                ItemStack installed = upgrades.getStackInSlot(i);
                if (i != slot && installed.getItem() instanceof StorageUpgradeItem
                        && installed.getItem() != candidate.getItem()) {
                    return false;
                }
            }
            return true;
        });
    }
}
