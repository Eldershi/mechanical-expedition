package expedition.itemtooltips;

import java.util.List;
import net.minecraft.ChatFormatting;
import net.minecraft.client.gui.screens.Screen;
import net.minecraft.core.component.DataComponents;
import net.minecraft.network.chat.Component;
import net.minecraft.world.food.FoodProperties;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.crafting.RecipeType;
import net.neoforged.api.distmarker.Dist;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.extensions.IItemStackExtension;
import net.neoforged.neoforge.event.entity.player.ItemTooltipEvent;

@Mod(value = "expedition_item_tooltips", dist = Dist.CLIENT)
public final class ExpeditionItemTooltips {
    public ExpeditionItemTooltips() {
        NeoForge.EVENT_BUS.addListener(ExpeditionItemTooltips::append);
    }

    private static void append(ItemTooltipEvent event) {
        ItemStack stack = event.getItemStack();
        if (stack.isEmpty()) return;
        // NeoForge adds this interface to ItemStack when patching the game classes.
        IItemStackExtension extension = (IItemStackExtension) (Object) stack;
        List<Component> lines = event.getToolTip();
        int burnTime = extension.getBurnTime(RecipeType.SMELTING);
        if (burnTime > 0) add(lines, "burn_time", burnTime);
        int maximumDamage = stack.getMaxDamage();
        if (stack.isDamageableItem() && !(event.getFlags().isAdvanced() && stack.isDamaged())) {
            add(lines, "durability", maximumDamage - stack.getDamageValue(), maximumDamage);
        }
        int enchantability = extension.getEnchantmentValue();
        if (enchantability > 0) add(lines, "enchantability", enchantability);
        FoodProperties food = stack.get(DataComponents.FOOD);
        if (food != null) add(lines, "food", food.nutrition(), food.saturation());
        if (stack.getMaxStackSize() > 1) add(lines, "stack_size", stack.getMaxStackSize());

        if (event.getFlags().isAdvanced() && Screen.hasShiftDown()) {
            add(lines, "translation_key", stack.getDescriptionId());
            if (!stack.getComponentsPatch().isEmpty()) {
                add(lines, "components", stack.getComponentsPatch());
            }
            stack.getTags().map(tag -> tag.location().toString()).sorted()
                .forEach(tag -> add(lines, "tag", "#" + tag));
        }
    }

    private static void add(List<Component> lines, String key, Object... arguments) {
        lines.add(Component.translatable("tooltip.expedition_item_tooltips." + key, arguments)
            .withStyle(ChatFormatting.GRAY));
    }
}
