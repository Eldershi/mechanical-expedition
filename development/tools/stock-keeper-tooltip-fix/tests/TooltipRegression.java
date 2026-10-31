import com.simibubi.create.content.logistics.BigItemStack;
import expedition.storage.mixin.StockKeeperTooltipMixin;
import java.lang.reflect.Method;
import net.minecraft.SharedConstants;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.TagParser;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.ItemStack;

/** Real vanilla ItemStack/NBT plus the installed Apotheosis UUID-writing bytecode. */
public class TooltipRegression extends StockKeeperTooltipMixin {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    private static ItemStack weapon(String affixes, int damage, String name) throws Exception {
        return ItemStack.m_41712_(TagParser.m_129359_("{id:'minecraft:diamond_sword',Count:1b,tag:{Damage:" + damage
            + ",display:{Name:'{\"text\":\"" + name + "\"}'},Enchantments:[{id:'minecraft:sharpness',lvl:7s}],"
            + "affix_data:{rarity:'apotheosis:mythic',sockets:3,affixes:{" + affixes + "}},"
            + "apoth_gems:[{id:'apotheosis:gem',Count:1b,tag:{gem:'apotheosis:core/diamond',rarity:'apotheosis:mythic'}}]}}"));
    }
    public static void main(String[] args) throws Exception {
        SharedConstants.m_142977_();
        Bootstrap.m_135870_();
        Method copy = StockKeeperTooltipMixin.class.getDeclaredMethod("expedition$tooltipCopy", BigItemStack.class);
        copy.setAccessible(true);
        Method uuids = Class.forName("InstalledGemUuidMethods").getMethod("getOrCreateUUIDs", CompoundTag.class, int.class);
        TooltipRegression mixin = new TooltipRegression();
        int cases = 0;
        for (int count : new int[]{1, 3, 6}) {
            ItemStack server = weapon("'apotheosis:light_weapon/attribute/murderous':0.63f", 0, "Named blade");
            CompoundTag original = server.m_41783_().m_6426_();
            ItemStack unpatched = server.m_41777_();
            uuids.invoke(null, unpatched.m_41737_("affix_data"), count);
            check(!ItemStack.m_150942_(server, unpatched), "Unpatched tooltip must reproduce lost stock match");
            ItemStack client = server.m_41777_();
            BigItemStack stock = new BigItemStack(client, 1);
            for (int repeat = 0; repeat < 4; repeat++) {
                ItemStack tooltip = (ItemStack) copy.invoke(mixin, stock);
                check(tooltip != client, "Tooltip must receive a distinct ItemStack");
                check(ItemStack.m_150942_(tooltip, client), "Tooltip copy must initially preserve every tag");
                uuids.invoke(null, tooltip.m_41737_("affix_data"), count);
                check(tooltip.m_41737_("affix_data").m_128437_("uuids", 11).size() == count, "Actual UUID generation must run");
                check(ItemStack.m_150942_(server, client), "Stock/order identity must survive tooltip generation");
                check(original.equals(client.m_41783_()), "All original NBT must be byte-value equivalent");
            }
            check(!ItemStack.m_150942_(client, weapon("'apotheosis:light_weapon/attribute/murderous':0.64f", 0, "Named blade")), "Different rolls stay distinct");
            check(!ItemStack.m_150942_(client, weapon("'apotheosis:light_weapon/attribute/murderous':0.63f", 1, "Named blade")), "Different durability stays distinct");
            check(!ItemStack.m_150942_(client, weapon("'apotheosis:light_weapon/attribute/murderous':0.63f", 0, "Other name")), "Different names stay distinct");
            cases++;
        }
        ItemStack prepared = weapon("'apotheosis:light_weapon/attribute/murderous':0.63f", 17, "Already initialized");
        uuids.invoke(null, prepared.m_41737_("affix_data"), 2);
        CompoundTag preparedBefore = prepared.m_41783_().m_6426_();
        ItemStack preparedTooltip = (ItemStack) copy.invoke(mixin, new BigItemStack(prepared, 1));
        uuids.invoke(null, preparedTooltip.m_41737_("affix_data"), 6);
        check(preparedBefore.equals(prepared.m_41783_()), "Existing UUIDs and damaged gear remain unchanged when more UUIDs are needed");
        ItemStack ordinary = ItemStack.m_41712_(TagParser.m_129359_("{id:'minecraft:stone',Count:64b}"));
        BigItemStack ordinaryEntry = new BigItemStack(ordinary, 640);
        ItemStack ordinaryTooltip = (ItemStack) copy.invoke(mixin, ordinaryEntry);
        check(ordinaryTooltip != ordinary && ItemStack.m_150942_(ordinary, ordinaryTooltip), "Ordinary items retain exact identity");
        check(ordinaryEntry.count == 640 && ordinaryTooltip.m_41613_() == 64, "Logical stock and physical stack counts are preserved");
        System.out.println("TOOLTIP_REGRESSION_OK: " + cases + " UUID counts; original failure reproduced; 12 protected hovers; affixes/gems/enchantments/name/damage preserved");
        System.out.println("PREEXISTING_UUIDS_AND_ORDINARY_ITEMS_OK");
    }
}
