package expedition.items;

import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Tier;
import vectorwing.farmersdelight.common.item.KnifeItem;

/** The pack's existing infinite knife, without cross-thread Rhino callbacks. */
public final class StableSuperKnife extends KnifeItem {
    public StableSuperKnife(Tier tier, float attackDamage, float attackSpeed, Item.Properties properties) {
        super(tier, attackDamage, attackSpeed, properties);
    }

    // Keep Farmer's Delight combat/mining hooks; only replace the Forge damage callback.
    public int getDamage(ItemStack stack) { return 0; }
    public boolean isDamageable() { return true; }
}
