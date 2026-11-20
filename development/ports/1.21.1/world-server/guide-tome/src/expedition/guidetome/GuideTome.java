package expedition.guidetome;

import com.mojang.logging.LogUtils;
import guideme.Guide;
import guideme.Guides;
import java.util.Comparator;
import java.util.List;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import net.neoforged.neoforge.event.server.ServerStartedEvent;
import vazkii.patchouli.common.book.BookRegistry;
import website.eccentric.tome.EccentricDataComponents;
import website.eccentric.tome.core.TomeData;
import website.eccentric.tome.core.TomeManager;

@Mod("expedition_guide_tome")
public final class GuideTome {
    private static final String DELIVERED = "expedition.guide_tome_granted";
    private static final List<String> NATIVE_GUIDES = List.of(
        "aether:book_of_lore",
        "ae2:guide",
        "alexscaves:cave_codex",
        "ars_nouveau:worn_notebook",
        "botania:lexicon",
        "create_enchantment_industry:blazes_enchanting_handbook",
        "eidolon_repraised:codex",
        "enigmaticlegacyplus:animal_guidebook",
        "enigmaticlegacyplus:hunter_guidebook",
        "enigmaticlegacyplus:sanguinary_handbook",
        "eternal_starlight:book",
        "ftbquests:book",
        "immersiveengineering:manual",
        "irons_spellbooks:chronicle",
        "legendary_monsters:guide_book",
        "maid_storage_manager:craft_guide",
        "maid_storage_manager:logistics_guide",
        "modernfoundry:encyclopedia",
        "modernfoundry:fantastic_foundry",
        "modernfoundry:materials_and_you",
        "modernfoundry:mighty_smelting",
        "modernfoundry:puny_smelting",
        "modernfoundry:tinkers_gadgetry",
        "solcarrot:food_book"
    );

    public GuideTome() {
        NeoForge.EVENT_BUS.addListener(GuideTome::logCatalogue);
        NeoForge.EVENT_BUS.addListener(GuideTome::giveTome);
    }

    static ItemStack createGuideTome() {
        ItemStack tome = TomeManager.createTome();
        for (String id : NATIVE_GUIDES) {
            var key = ResourceLocation.parse(id);
            if (BuiltInRegistries.ITEM.containsKey(key)) {
                tome = TomeManager.addBookToTome(tome, new ItemStack(BuiltInRegistries.ITEM.get(key)));
            }
        }
        for (var book : BookRegistry.INSTANCE.books.values().stream()
                .filter(book -> !book.noBook)
                .sorted(Comparator.comparing(book -> book.id)).toList()) {
            tome = TomeManager.addBookToTome(tome, book.getBookItem());
        }
        for (var guide : Guides.getAll().stream().sorted(Comparator.comparing(Guide::getId)).toList()) {
            if (guide.getStartPage() != null) {
                tome = TomeManager.addBookToTome(tome, Guides.createGuideItem(guide.getId()));
            }
        }
        return tome;
    }

    private static void logCatalogue(ServerStartedEvent event) {
        var books = createGuideTome().getOrDefault(EccentricDataComponents.TOME_DATA.get(), TomeData.EMPTY);
        LogUtils.getLogger().info("Expedition guide tome contains {} books", books.getTotalBookCount());
    }

    private static void giveTome(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player)) {
            return;
        }
        var persistent = player.getPersistentData();
        var retained = persistent.getCompound(Player.PERSISTED_NBT_TAG);
        if (!retained.getBoolean(DELIVERED) && player.getInventory().add(createGuideTome())) {
            retained.putBoolean(DELIVERED, true);
            persistent.put(Player.PERSISTED_NBT_TAG, retained);
        }
    }
}
