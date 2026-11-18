package expedition.equipment;

import java.util.List;
import java.util.Set;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.TagKey;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.neoforged.fml.common.Mod;
import net.neoforged.neoforge.common.NeoForge;
import net.neoforged.neoforge.common.util.TriState;
import net.neoforged.neoforge.event.entity.player.PlayerEvent;
import top.theillusivec4.curios.api.CuriosApi;
import top.theillusivec4.curios.api.SlotAttribute;
import top.theillusivec4.curios.api.event.CurioAttributeModifierEvent;
import top.theillusivec4.curios.api.event.CurioCanEquipEvent;
import top.theillusivec4.curios.api.type.capability.ICuriosItemHandler;
import top.theillusivec4.curios.api.type.inventory.IDynamicStackHandler;

@Mod("expedition_equipment_rules")
public final class CuriosRules {
    private static final String LAYOUT_MARKER = "expeditionEquipmentLayoutV2";
    private static final ResourceLocation RING = ResourceLocation.parse("cataclysm:ring_of_grudged");
    private static final ResourceLocation CRITICAL = ResourceLocation.parse("cataclysm:additional_critical_damage");
    private static final TagKey<Item> BACKPACKS = itemTag("expedition:backpacks");
    private static final TagKey<Item> AETHER_SHIELDS = itemTag("aether:accessories_shields");
    private static final TagKey<Item> AETHER_MISC = itemTag("aether:accessories_miscellaneous");
    private static final TagKey<Item> GENERIC = itemTag("curios:curio");
    private static final Set<String> UNLOCKABLE = Set.of("talisman", "rune", "scroll", "spellstone");
    private static final Set<String> TYPED = Set.of(
        "back", "backpack", "belt", "body", "bracelet", "charm", "hands", "head", "necklace", "ring",
        "mechanisms", "hostility_curse", "an_focus", "bundle", "feet", "spellbook", "adv_pattern_encoder",
        "brooch", "deep_learner", "pouch", "tiab", "talisman", "rune", "scroll", "spellstone"
    );
    private static final List<TagKey<Item>> TYPED_TAGS = TYPED.stream().map(CuriosRules::slotTag).toList();

    public CuriosRules() {
        CuriosApi.registerCurioPredicate(ResourceLocation.parse("expedition:backpack"),
            result -> result.stack().is(BACKPACKS));
        NeoForge.EVENT_BUS.addListener(CuriosRules::checkEquip);
        NeoForge.EVENT_BUS.addListener(CuriosRules::checkAttribute);
        NeoForge.EVENT_BUS.addListener(CuriosRules::reconcileOnLogin);
    }

    private static TagKey<Item> itemTag(String id) {
        return TagKey.create(Registries.ITEM, ResourceLocation.parse(id));
    }

    private static TagKey<Item> slotTag(String slot) {
        return TagKey.create(Registries.ITEM, ResourceLocation.fromNamespaceAndPath("curios", slot));
    }

    private static boolean allowed(String slot, ItemStack stack) {
        if (stack.is(AETHER_SHIELDS) || (stack.is(BACKPACKS) != slot.equals("backpack"))) {
            return false;
        }
        if (stack.is(AETHER_MISC)) {
            return slot.equals("curio");
        }
        if (slot.equals("curio")) {
            return stack.is(GENERIC) && TYPED_TAGS.stream().noneMatch(stack::is);
        }
        return TYPED.contains(slot) && stack.is(slotTag(slot));
    }

    private static void checkEquip(CurioCanEquipEvent event) {
        if (!allowed(event.getSlotContext().identifier(), event.getStack())) {
            event.setEquipResult(TriState.FALSE);
        }
    }

    private static void checkAttribute(CurioAttributeModifierEvent event) {
        var fixedSlots = event.getModifiers().keySet().stream()
            .filter(key -> key.value() instanceof SlotAttribute slot && !UNLOCKABLE.contains(slot.getIdentifier()))
            .toList();
        fixedSlots.forEach(event::removeAttribute);

        if (event.getSlotContext().identifier().equals("ring")
                && event.getItemStack().is(BuiltInRegistries.ITEM.get(RING))) {
            BuiltInRegistries.ATTRIBUTE.getHolder(CRITICAL).ifPresent(attribute -> {
                if (!event.getModifiers().containsKey(attribute)) {
                    event.addModifier(attribute, new AttributeModifier(event.getId(), 10,
                        AttributeModifier.Operation.ADD_VALUE));
                }
            });
        }
    }

    private static void reconcileOnLogin(PlayerEvent.PlayerLoggedInEvent event) {
        if (!(event.getEntity() instanceof ServerPlayer player) || player.getPersistentData().getBoolean(LAYOUT_MARKER)) {
            return;
        }
        CuriosApi.getCuriosInventory(player).ifPresent(inventory -> {
            reconcile(inventory);
            player.getPersistentData().putBoolean(LAYOUT_MARKER, true);
        });
    }

    static void reconcile(ICuriosItemHandler inventory) {
        var slots = inventory.getCurios();
        slots.forEach((slot, handler) -> {
            if (!UNLOCKABLE.contains(slot)) {
                handler.clearModifiers();
                handler.clearCachedModifiers();
                handler.update();
            }
        });
        slots.forEach((slot, handler) -> {
            moveMisplaced(inventory, slot, handler.getStacks(), false);
            if (handler.hasCosmetic()) {
                moveMisplaced(inventory, slot, handler.getCosmeticStacks(), true);
            }
        });
        inventory.handleInvalidStacks();
    }

    private static void moveMisplaced(ICuriosItemHandler inventory, String slot, IDynamicStackHandler source,
                                      boolean cosmetic) {
        for (int index = 0; index < source.getSlots(); index++) {
            ItemStack original = source.getStackInSlot(index);
            if (original.isEmpty() || allowed(slot, original)) {
                continue;
            }
            ItemStack remainder = original.copy();
            for (var row : inventory.getCurios().entrySet()) {
                if (remainder.isEmpty()) {
                    break;
                }
                if (!allowed(row.getKey(), remainder) || (cosmetic && !row.getValue().hasCosmetic())) {
                    continue;
                }
                var target = cosmetic ? row.getValue().getCosmeticStacks() : row.getValue().getStacks();
                for (int destination = 0; destination < target.getSlots() && !remainder.isEmpty(); destination++) {
                    if (target.getStackInSlot(destination).isEmpty() && target.isItemValid(destination, remainder)) {
                        remainder = target.insertItem(destination, remainder, false);
                        source.setStackInSlot(index, remainder);
                    }
                }
            }
            if (!remainder.isEmpty()) {
                inventory.loseInvalidStack(remainder);
                source.setStackInSlot(index, ItemStack.EMPTY);
            }
        }
    }
}
